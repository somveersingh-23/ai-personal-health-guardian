package com.healthguardian.app.feature.sensors.network

import com.healthguardian.app.feature.sensors.domain.ObservationGovernance
import com.healthguardian.app.feature.sensors.domain.SensorReading
import com.healthguardian.app.feature.sensors.domain.SeriesReading
import com.healthguardian.app.feature.sensors.domain.SessionReading
import java.net.HttpURLConnection
import java.net.URL
import java.net.URI
import java.time.Instant
import java.util.UUID
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

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
    private val governanceProvider: ObservationGovernanceProvider? = null,
    private val localUserId: Int,
) : SensorBackend {
    private val endpoint = baseUrl.trimEnd('/').also {
        val uri = URI(it)
        val isLocalDevelopment = uri.scheme == "http" &&
            uri.host in setOf("10.0.2.2", "127.0.0.1", "localhost", "[::1]")
        require(uri.host != null && (uri.scheme == "https" || isLocalDevelopment)) {
            "sensor backend must use HTTPS outside local development"
        }
        require(localUserId > 0) { "local profile ID must be positive" }
        require(uri.rawUserInfo == null && uri.rawQuery == null && uri.rawFragment == null &&
            (uri.port == -1 || uri.port in 1..65535) && uri.rawPath.isNullOrEmpty()) {
            "sensor backend must be an origin URL without credentials, path, query or fragment"
        }
    }

    override suspend fun upload(readings: List<SensorReading>) {
        readings.forEach {
            if (it is SeriesReading && (it.samples.isEmpty() || it.samples.size > 10_000)) {
                throw SensorInputException("series_outside_supported_sample_limit")
            }
            if (it is SessionReading && it.stages.size > 500) {
                throw SensorInputException("session_outside_supported_stage_limit")
            }
        }
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
        val querySeparator = if (path.contains('?')) '&' else '?'
        val localIdentity = "$querySeparator" + "user_id=$localUserId"
        val connection = (URL(endpoint + path + localIdentity).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 15_000
            readTimeout = 30_000
            doOutput = true
            useCaches = false
            instanceFollowRedirects = false
            setRequestProperty("Content-Type", "application/json; charset=utf-8")
            setRequestProperty("Accept", "application/json")
        }
        try {
            connection.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
            if (connection.responseCode !in 200..299) {
                // Never include health measurements in errors or logs.
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

class SensorInputException(val reasonCode: String) : Exception(reasonCode)
