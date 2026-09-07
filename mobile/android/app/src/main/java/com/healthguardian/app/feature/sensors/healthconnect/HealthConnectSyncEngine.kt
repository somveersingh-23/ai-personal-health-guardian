package com.healthguardian.app.feature.sensors.healthconnect

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
import com.healthguardian.app.feature.sensors.network.SensorBackend
import com.healthguardian.app.feature.sensors.network.SensorBackendException
import com.healthguardian.app.feature.sensors.network.SensorInputException
import java.time.Duration
import java.time.Instant
import kotlin.reflect.KClass
import com.healthguardian.app.feature.sensors.domain.SensorReading
import com.healthguardian.app.feature.sensors.sync.SensorConfigurationException
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive

data class RecordSyncResult(
    val recordType: String,
    val upserted: Int,
    val deleted: Int,
    val reconciledAfterExpiredToken: Boolean,
    val permissionRevoked: Boolean = false,
    val failureCode: String? = null,
)

data class SyncSummary(val results: List<RecordSyncResult>) {
    val upserted: Int = results.sumOf(RecordSyncResult::upserted)
    val deleted: Int = results.sumOf(RecordSyncResult::deleted)
    val revokedTypes: List<String> = results.filter { it.permissionRevoked }.map { it.recordType }
    val failedTypes: List<String> = results.filter { it.failureCode != null }.map { it.recordType }
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

    private suspend fun ensureSyncActive() {
        currentCoroutineContext().ensureActive()
        if (tokenStore.isPaused()) throw SensorConfigurationException("sensor sync is paused")
    }

    suspend fun syncAll(): SyncSummary {
        ensureSyncActive()
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
            } catch (error: SensorInputException) {
                RecordSyncResult(name, 0, 0, false, failureCode = error.reasonCode)
            } catch (error: SensorBackendException) {
                if (error.statusCode == 429 || error.statusCode >= 500) throw error
                RecordSyncResult(name, 0, 0, false, failureCode = "backend_${error.statusCode}")
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
            ensureSyncActive()
            val response = client.getChanges(token)
            if (response.changesTokenExpired) {
                tokenStore.clear(name)
                return fullSnapshot(recordType, name)
            }
            val records = mutableListOf<SensorReading>()
            val deletedIds = mutableListOf<String>()
            suspend fun flush() {
                ensureSyncActive()
                if (records.isNotEmpty()) {
                    backend.upload(records.toList())
                    upserted += records.size
                    records.clear()
                }
                if (deletedIds.isNotEmpty()) {
                    backend.delete(name, deletedIds.toList())
                    deleted += deletedIds.size
                    deletedIds.clear()
                }
            }
            for (change in response.changes) {
                when (change) {
                    is UpsertionChange -> {
                        if (deletedIds.isNotEmpty()) flush()
                        if (change.record.metadata.dataOrigin.packageName != applicationPackage) {
                            records.add(HealthConnectMapper.map(change.record, permissionState))
                        }
                    }
                    is DeletionChange -> {
                        if (records.isNotEmpty()) flush()
                        deletedIds.add(change.recordId)
                    }
                }
            }
            flush()
            token = response.nextChangesToken
            hasMore = response.hasMore
            // Advance only after every remote operation for this page succeeds.
            ensureSyncActive()
            tokenStore.save(name, token, Instant.now())
        } while (hasMore)
        return RecordSyncResult(name, upserted, deleted, false)
    }

    private suspend fun fullSnapshot(
        recordType: KClass<out Record>,
        name: String,
    ): RecordSyncResult {
        // Reserve token first: changes arriving during the snapshot are replayed next sync.
        ensureSyncActive()
        val reservedToken = client.getChangesToken(ChangesTokenRequest(setOf(recordType)))
        val windowEnd = Instant.now()
        val windowStart = windowEnd.minus(Duration.ofDays(30))
        ensureSyncActive()
        val reconciliation = backend.beginReconciliation(name, windowStart, windowEnd)
        var mappedCount = 0
        readAllPages(recordType, windowStart, windowEnd) { page ->
            val records = page.filter {
                it.metadata.dataOrigin.packageName != applicationPackage
            }
            val mapped = records.map { HealthConnectMapper.map(it, permissionState) }
            ensureSyncActive()
            if (mapped.isNotEmpty()) backend.upload(mapped)
            if (records.isNotEmpty()) {
                ensureSyncActive()
                backend.appendReconciliationRecords(
                    reconciliation,
                    records.map { it.metadata.id },
                )
            }
            mappedCount += mapped.size
        }
        ensureSyncActive()
        backend.completeReconciliation(reconciliation)
        ensureSyncActive()
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
            ensureSyncActive()
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
