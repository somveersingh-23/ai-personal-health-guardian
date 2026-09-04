package com.healthguardian.sensor.healthconnect

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.changes.DeletionChange
import androidx.health.connect.client.changes.UpsertionChange
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.HeartRateVariabilityRmssdRecord
import androidx.health.connect.client.records.OxygenSaturationRecord
import androidx.health.connect.client.records.Record
import androidx.health.connect.client.records.RespiratoryRateRecord
import androidx.health.connect.client.records.RestingHeartRateRecord
import androidx.health.connect.client.records.SkinTemperatureRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.request.ChangesTokenRequest
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import com.healthguardian.sensor.network.SensorBackend
import java.time.Duration
import java.time.Instant
import kotlin.reflect.KClass

data class RecordSyncResult(
    val recordType: String,
    val upserted: Int,
    val deleted: Int,
    val reconciledAfterExpiredToken: Boolean,
    val permissionRevoked: Boolean = false,
)

data class SyncSummary(val results: List<RecordSyncResult>) {
    val upserted: Int = results.sumOf(RecordSyncResult::upserted)
    val deleted: Int = results.sumOf(RecordSyncResult::deleted)
    val revokedTypes: List<String> = results.filter { it.permissionRevoked }.map { it.recordType }
}

class HealthConnectSyncEngine(
    private val applicationPackage: String,
    private val client: HealthConnectClient,
    private val tokenStore: SyncTokenStore,
    private val backend: SensorBackend,
) {
    constructor(
        context: Context,
        client: HealthConnectClient,
        tokenStore: SyncTokenStore,
        backend: SensorBackend,
    ) : this(context.packageName, client, tokenStore, backend)

    private var permissionState = "granted_foreground"

    suspend fun syncAll(): SyncSummary {
        check(!tokenStore.isPaused()) { "sensor sync is paused by the user" }
        val granted = client.permissionController.getGrantedPermissions()
        permissionState = if (HealthConnectAccess.optionalBackgroundPermission() in granted) {
            "granted_background"
        } else {
            "granted_foreground"
        }
        val results = HealthConnectAccess.supportedRecordTypes(client).map { recordType ->
            val name = recordType.simpleName ?: error("record type has no stable name")
            if (HealthPermission.getReadPermission(recordType) !in granted) {
                // If permission is missing/revoked, clear stored change token immediately
                tokenStore.clear(name)
                return@map RecordSyncResult(name, 0, 0, false, permissionRevoked = true)
            }
            try {
                syncRecordType(recordType)
            } catch (_: SecurityException) {
                // A permission can be revoked between the preflight check and the read.
                tokenStore.clear(name)
                RecordSyncResult(name, 0, 0, false, permissionRevoked = true)
            }
        }
        return SyncSummary(results)
    }

    private suspend fun syncRecordType(recordType: KClass<out Record>): RecordSyncResult {
        val name = recordType.simpleName ?: error("record type has no stable name")
        val stored = tokenStore.load(name)
        if (stored == null) return fullSnapshot(recordType, name)

        var token = stored.token
        var upserted = 0
        var deleted = 0
        var hasMore: Boolean
        do {
            val response = client.getChanges(token)
            if (response.changesTokenExpired) {
                tokenStore.clear(name)
                return fullSnapshot(recordType, name)
            }
            val records = response.changes
                .filterIsInstance<UpsertionChange>()
                .map(UpsertionChange::record)
                .filter { it.metadata.dataOrigin.packageName != applicationPackage }
                .map { HealthConnectMapper.map(it, permissionState) }
            val deletedIds = response.changes
                .filterIsInstance<DeletionChange>()
                .map(DeletionChange::recordId)

            if (records.isNotEmpty()) backend.upload(records)
            if (deletedIds.isNotEmpty()) backend.delete(name, deletedIds)

            upserted += records.size
            deleted += deletedIds.size
            token = response.nextChangesToken
            hasMore = response.hasMore
            // Advance only after every remote operation for this page succeeds.
            tokenStore.save(name, token, Instant.now())
        } while (hasMore)
        return RecordSyncResult(name, upserted, deleted, false)
    }

    private suspend fun fullSnapshot(
        recordType: KClass<out Record>,
        name: String,
    ): RecordSyncResult {
        // Reserve token first: changes arriving during the snapshot are replayed next sync.
        val reservedToken = client.getChangesToken(ChangesTokenRequest(setOf(recordType)))
        val windowEnd = Instant.now()
        val windowStart = windowEnd.minus(Duration.ofDays(30))
        val reconciliation = backend.beginReconciliation(name, windowStart, windowEnd)
        var mappedCount = 0
        readAllPages(recordType, windowStart, windowEnd) { page ->
            val records = page.filter {
                it.metadata.dataOrigin.packageName != applicationPackage
            }
            val mapped = records.map { HealthConnectMapper.map(it, permissionState) }
            if (mapped.isNotEmpty()) backend.upload(mapped)
            if (records.isNotEmpty()) {
                backend.appendReconciliationRecords(
                    reconciliation,
                    records.map { it.metadata.id },
                )
            }
            mappedCount += mapped.size
        }
        backend.completeReconciliation(reconciliation)
        tokenStore.save(name, reservedToken, Instant.now())
        return RecordSyncResult(name, mappedCount, 0, true)
    }

    private suspend fun readAllPages(
        recordType: KClass<out Record>,
        start: Instant,
        end: Instant,
        consume: suspend (List<Record>) -> Unit,
    ) = when (recordType) {
        HeartRateRecord::class -> readPages(HeartRateRecord::class, start, end, consume)
        RestingHeartRateRecord::class -> readPages(
            RestingHeartRateRecord::class,
            start,
            end,
            consume,
        )
        HeartRateVariabilityRmssdRecord::class -> {
            readPages(HeartRateVariabilityRmssdRecord::class, start, end, consume)
        }
        OxygenSaturationRecord::class -> readPages(OxygenSaturationRecord::class, start, end, consume)
        RespiratoryRateRecord::class -> readPages(RespiratoryRateRecord::class, start, end, consume)
        StepsRecord::class -> readPages(StepsRecord::class, start, end, consume)
        SleepSessionRecord::class -> readPages(SleepSessionRecord::class, start, end, consume)
        ActiveCaloriesBurnedRecord::class -> readPages(
            ActiveCaloriesBurnedRecord::class,
            start,
            end,
            consume,
        )
        SkinTemperatureRecord::class -> readPages(SkinTemperatureRecord::class, start, end, consume)
        else -> error("unsupported record type: $recordType")
    }

    private suspend fun <T : Record> readPages(
        recordType: KClass<T>,
        start: Instant,
        end: Instant,
        consume: suspend (List<Record>) -> Unit,
    ) {
        var pageToken: String? = null
        do {
            val response = client.readRecords(
                ReadRecordsRequest(
                    recordType = recordType,
                    timeRangeFilter = TimeRangeFilter.between(start, end),
                    pageSize = 500,
                    pageToken = pageToken,
                ),
            )
            consume(response.records)
            pageToken = response.pageToken?.takeIf(String::isNotEmpty)
        } while (pageToken != null)
    }
}
