package com.healthguardian.sensor.healthconnect

import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.aggregate.AggregateMetric
import androidx.health.connect.client.aggregate.AggregationResult
import androidx.health.connect.client.aggregate.AggregationResultGroupedByDuration
import androidx.health.connect.client.aggregate.AggregationResultGroupedByPeriod
import androidx.health.connect.client.changes.Change
import androidx.health.connect.client.changes.DeletionChange
import androidx.health.connect.client.changes.UpsertionChange
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.Record
import androidx.health.connect.client.records.metadata.DataOrigin
import androidx.health.connect.client.records.metadata.Device
import androidx.health.connect.client.records.metadata.Metadata
import androidx.health.connect.client.request.AggregateGroupByDurationRequest
import androidx.health.connect.client.request.AggregateGroupByPeriodRequest
import androidx.health.connect.client.request.AggregateRequest
import androidx.health.connect.client.request.ChangesTokenRequest
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.response.ChangesResponse
import androidx.health.connect.client.response.ReadRecordResponse
import androidx.health.connect.client.response.ReadRecordsResponse
import androidx.health.connect.client.time.TimeRangeFilter
import androidx.health.connect.client.testing.populatedWithTestValues
import com.healthguardian.sensor.domain.SensorReading
import com.healthguardian.sensor.network.SensorBackend
import com.healthguardian.sensor.network.ReconciliationHandle
import java.time.Instant
import javax.crypto.SecretKey
import javax.crypto.spec.SecretKeySpec
import kotlin.reflect.KClass

internal class TestSyncTokenCipher : AesGcmSyncTokenCipher() {
    private val key = SecretKeySpec(ByteArray(32) { index -> (index + 1).toByte() }, "AES")

    override fun secretKey(): SecretKey = key
}

fun createTestMetadata(
    id: String,
    dataOriginPackage: String = "com.samsung.shealth",
    lastModifiedTime: Instant = Instant.parse("2026-08-29T10:00:00Z"),
    device: Device? = null,
): Metadata = Metadata.autoRecorded(device ?: Device(type = Device.TYPE_WATCH))
    .populatedWithTestValues(
        id = id,
        dataOrigin = DataOrigin(dataOriginPackage),
        lastModifiedTime = lastModifiedTime,
    )

class FakePermissionController(
    var grantedPermissions: Set<String> = emptySet(),
) : PermissionController {
    var revokeCallCount: Int = 0
    var revokeFailure: Exception? = null

    override suspend fun getGrantedPermissions(): Set<String> = grantedPermissions

    override suspend fun revokeAllPermissions() {
        revokeCallCount += 1
        revokeFailure?.let { throw it }
        grantedPermissions = emptySet()
    }
}

class FakeHealthConnectFeatures(
    var skinTemperatureAvailable: Boolean = true,
    var backgroundAvailable: Boolean = true,
    var historyAvailable: Boolean = true,
) : androidx.health.connect.client.HealthConnectFeatures {
    override fun getFeatureStatus(feature: Int): Int = when (feature) {
        androidx.health.connect.client.HealthConnectFeatures.FEATURE_SKIN_TEMPERATURE -> {
            if (skinTemperatureAvailable) androidx.health.connect.client.HealthConnectFeatures.FEATURE_STATUS_AVAILABLE
            else androidx.health.connect.client.HealthConnectFeatures.FEATURE_STATUS_UNAVAILABLE
        }
        androidx.health.connect.client.HealthConnectFeatures.FEATURE_READ_HEALTH_DATA_IN_BACKGROUND -> {
            if (backgroundAvailable) androidx.health.connect.client.HealthConnectFeatures.FEATURE_STATUS_AVAILABLE
            else androidx.health.connect.client.HealthConnectFeatures.FEATURE_STATUS_UNAVAILABLE
        }
        androidx.health.connect.client.HealthConnectFeatures.FEATURE_READ_HEALTH_DATA_HISTORY -> {
            if (historyAvailable) androidx.health.connect.client.HealthConnectFeatures.FEATURE_STATUS_AVAILABLE
            else androidx.health.connect.client.HealthConnectFeatures.FEATURE_STATUS_UNAVAILABLE
        }
        else -> androidx.health.connect.client.HealthConnectFeatures.FEATURE_STATUS_UNAVAILABLE
    }
}

class FakeHealthConnectClient(
    val fakePermissions: FakePermissionController = FakePermissionController(),
    val fakeFeatures: FakeHealthConnectFeatures = FakeHealthConnectFeatures(),
) : HealthConnectClient {
    override val permissionController: PermissionController = fakePermissions
    override val features: androidx.health.connect.client.HealthConnectFeatures = fakeFeatures

    var changesResponses: MutableMap<String, ChangesResponse> = mutableMapOf()
    var readRecordsMap: MutableMap<KClass<out Record>, List<Record>> = mutableMapOf()
    var readRecordsRequestCount: Int = 0
    var tokenGenerator: (Set<KClass<out Record>>) -> String = { "token_${it.first().simpleName}_1" }
    var throwSecurityExceptionOnSync: Boolean = false

    override suspend fun getChangesToken(request: ChangesTokenRequest): String {
        return tokenGenerator(request.recordTypes)
    }

    override suspend fun getChanges(changesToken: String): ChangesResponse {
        if (throwSecurityExceptionOnSync) {
            throw SecurityException("Health Connect permission revoked during sync")
        }
        return changesResponses[changesToken] ?: ChangesResponse(
            changes = emptyList(),
            nextChangesToken = "${changesToken}_next",
            hasMore = false,
            changesTokenExpired = false,
        )
    }

    @Suppress("UNCHECKED_CAST")
    override suspend fun <T : Record> readRecords(request: ReadRecordsRequest<T>): ReadRecordsResponse<T> {
        readRecordsRequestCount += 1
        val all = (readRecordsMap[request.recordType] ?: emptyList()) as List<T>
        val start = request.pageToken?.toIntOrNull() ?: 0
        val end = minOf(start + request.pageSize, all.size)
        return ReadRecordsResponse(
            records = all.subList(start, end),
            pageToken = end.takeIf { it < all.size }?.toString(),
        )
    }

    override suspend fun insertRecords(records: List<Record>): androidx.health.connect.client.response.InsertRecordsResponse {
        return androidx.health.connect.client.response.InsertRecordsResponse(emptyList())
    }

    override suspend fun updateRecords(records: List<Record>) {}

    override suspend fun deleteRecords(
        recordType: KClass<out Record>,
        recordIdsList: List<String>,
        clientRecordIdsList: List<String>,
    ) {}

    override suspend fun deleteRecords(
        recordType: KClass<out Record>,
        timeRangeFilter: TimeRangeFilter,
    ) {}

    override suspend fun <T : Record> readRecord(
        recordType: KClass<T>,
        recordId: String,
    ): ReadRecordResponse<T> {
        throw NotImplementedError()
    }

    override suspend fun aggregate(request: AggregateRequest): AggregationResult {
        throw NotImplementedError()
    }

    override suspend fun aggregateGroupByDuration(
        request: AggregateGroupByDurationRequest,
    ): List<AggregationResultGroupedByDuration> = emptyList()

    override suspend fun aggregateGroupByPeriod(
        request: AggregateGroupByPeriodRequest,
    ): List<AggregationResultGroupedByPeriod> = emptyList()
}

class FakeSensorBackend : SensorBackend {
    val uploadedBatches = mutableListOf<List<SensorReading>>()
    val deletedRequests = mutableListOf<Pair<String, List<String>>>()
    val reconciledRequests = mutableListOf<ReconciliationCall>()
    var shouldFailUpload: Boolean = false
    private val pendingReconciliations = mutableMapOf<String, ReconciliationCall>()

    data class ReconciliationCall(
        val sourceRecordType: String,
        val windowStart: Instant,
        val windowEnd: Instant,
        val authoritativeIds: List<String>,
    )

    override suspend fun upload(readings: List<SensorReading>) {
        if (shouldFailUpload) throw IllegalStateException("Backend upload simulated failure")
        uploadedBatches.add(readings)
    }

    override suspend fun delete(sourceRecordType: String, sourceRecordIds: List<String>) {
        deletedRequests.add(sourceRecordType to sourceRecordIds)
    }

    override suspend fun beginReconciliation(
        sourceRecordType: String,
        windowStart: Instant,
        windowEnd: Instant,
    ): ReconciliationHandle {
        val handle = ReconciliationHandle(
            sessionId = "fake-reconciliation-${pendingReconciliations.size + reconciledRequests.size}",
            sourceRecordType = sourceRecordType,
        )
        pendingReconciliations[handle.sessionId] =
            ReconciliationCall(sourceRecordType, windowStart, windowEnd, emptyList())
        return handle
    }

    override suspend fun appendReconciliationRecords(
        handle: ReconciliationHandle,
        authoritativeIds: List<String>,
    ) {
        val existing = checkNotNull(pendingReconciliations[handle.sessionId])
        pendingReconciliations[handle.sessionId] = existing.copy(
            authoritativeIds = existing.authoritativeIds + authoritativeIds,
        )
    }

    override suspend fun completeReconciliation(handle: ReconciliationHandle) {
        reconciledRequests.add(checkNotNull(pendingReconciliations.remove(handle.sessionId)))
    }
}
