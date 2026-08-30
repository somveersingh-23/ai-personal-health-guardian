package com.healthguardian.sensor.network

import com.healthguardian.sensor.domain.ObservationGovernance
import com.healthguardian.sensor.domain.SensorReading
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant
import java.util.UUID
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

fun interface AccessTokenProvider {
    suspend fun accessToken(): String
}

fun interface ObservationGovernanceProvider {
    suspend fun currentGovernance(): ObservationGovernance
}

data class ReconciliationHandle(
    val sessionId: String,
    val sourceRecordType: String,
)

interface SensorBackend {
    suspend fun upload(readings: List<SensorReading>)
    suspend fun delete(sourceRecordType: String, sourceRecordIds: List<String>)
    suspend fun beginReconciliation(
        sourceRecordType: String,
        windowStart: Instant,
        windowEnd: Instant,
    ): ReconciliationHandle

    suspend fun appendReconciliationRecords(
        handle: ReconciliationHandle,
        authoritativeIds: List<String>,
    )

    suspend fun completeReconciliation(handle: ReconciliationHandle)

    suspend fun reconcile(
        sourceRecordType: String,
        windowStart: Instant,
        windowEnd: Instant,
        authoritativeIds: List<String>,
    ) {
        val handle = beginReconciliation(sourceRecordType, windowStart, windowEnd)
        authoritativeIds.distinct().chunked(500).forEach { ids ->
            if (ids.isNotEmpty()) appendReconciliationRecords(handle, ids)
        }
        completeReconciliation(handle)
    }
}

class HttpSensorBackend(
    baseUrl: String,
    private val tokenProvider: AccessTokenProvider,
    private val governanceProvider: ObservationGovernanceProvider? = null,
) : SensorBackend {
    private val endpoint = baseUrl.trimEnd('/').also {
        require(it.startsWith("https://")) { "sensor backend must use HTTPS" }
    }

    override suspend fun upload(readings: List<SensorReading>) {
        val governance = governanceProvider?.currentGovernance()
        readings.chunked(500).forEach { batch ->
            val payload = JSONObject()
                .put("schema_version", if (governance == null) "2.0.0" else "3.0.0")
                .put("batch_id", UUID.randomUUID().toString())
                .put("events", JSONArray(batch.map { it.toJson(governance) }))
            post("/api/v1/member2/events/batch", payload)
        }
    }

    override suspend fun delete(sourceRecordType: String, sourceRecordIds: List<String>) {
        sourceRecordIds.distinct().chunked(500).forEach { ids ->
            post(
                "/api/v1/member2/sync/deletions",
                JSONObject()
                    .put("source", "health_connect")
                    .put("source_record_type", sourceRecordType)
                    .put("source_record_ids", JSONArray(ids))
                    .put("deleted_at", Instant.now().toString()),
            )
        }
    }

    override suspend fun beginReconciliation(
        sourceRecordType: String,
        windowStart: Instant,
        windowEnd: Instant,
    ): ReconciliationHandle {
        val sessionId = UUID.randomUUID().toString()
        post(
            "/api/v1/member2/sync/reconcile/sessions",
            JSONObject()
                .put("session_id", sessionId)
                .put("source", "health_connect")
                .put("source_record_type", sourceRecordType)
                .put("window_start", windowStart.toString())
                .put("window_end", windowEnd.toString()),
        )
        return ReconciliationHandle(sessionId, sourceRecordType)
    }

    override suspend fun appendReconciliationRecords(
        handle: ReconciliationHandle,
        authoritativeIds: List<String>,
    ) {
        authoritativeIds.distinct().chunked(500).forEach { ids ->
            if (ids.isNotEmpty()) {
                post(
                    "/api/v1/member2/sync/reconcile/sessions/${handle.sessionId}/records",
                    JSONObject().put("source_record_ids", JSONArray(ids)),
                )
            }
        }
    }

    override suspend fun completeReconciliation(handle: ReconciliationHandle) {
        post(
            "/api/v1/member2/sync/reconcile/sessions/${handle.sessionId}/complete",
            JSONObject().put("complete_snapshot", true),
        )
    }

    private suspend fun post(path: String, payload: JSONObject): JSONObject = withContext(Dispatchers.IO) {
        val token = tokenProvider.accessToken().trim()
        require(token.isNotEmpty()) { "authenticated access token is required" }
        val connection = (URL(endpoint + path).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 15_000
            readTimeout = 30_000
            doOutput = true
            useCaches = false
            setRequestProperty("Authorization", "Bearer $token")
            setRequestProperty("Content-Type", "application/json; charset=utf-8")
            setRequestProperty("Accept", "application/json")
        }
        try {
            connection.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
            if (connection.responseCode !in 200..299) {
                // Never include the health payload or access token in errors/logs.
                throw SensorBackendException(connection.responseCode)
            }
            val responseBytes = connection.inputStream.use { it.readBytes() }
            if (responseBytes.isEmpty()) JSONObject() else JSONObject(responseBytes.toString(Charsets.UTF_8))
        } finally {
            connection.disconnect()
        }
    }
}

class SensorBackendException(val statusCode: Int) : Exception("sensor backend rejected request ($statusCode)")
