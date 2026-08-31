package com.healthguardian.member3.data

import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.util.UUID

interface Member3Gateway {
    fun askAssistant(userId: String, question: String): String
    fun listInsights(userId: String): List<HealthInsight>
    fun listAlerts(userId: String): List<GuardianAlert>
    fun listCaregivers(userId: String): List<Caregiver>
    fun inviteCaregiver(userId: String, caregiverUserRef: String, relationshipLabel: String): Caregiver
    fun startEmergency(userId: String, reason: String): EmergencyWorkflow
}

class Member3ApiClient(
    private val baseUrl: String,
    private val sessionManager: SessionManager? = null,
) : Member3Gateway {
    private fun request(path: String, method: String = "GET", body: JSONObject? = null): JSONObject {
        val connection = URL("${baseUrl.trimEnd('/')}$path").openConnection() as HttpURLConnection
        return try {
            connection.requestMethod = method
            connection.connectTimeout = 8_000
            connection.readTimeout = 12_000
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Content-Type", "application/json")
            sessionManager?.token?.let { token ->
                if (token.isNotBlank()) {
                    connection.setRequestProperty("Authorization", "Bearer $token")
                }
            }
            body?.let {
                connection.doOutput = true
                connection.outputStream.bufferedWriter().use { writer -> writer.write(it.toString()) }
            }
            val stream = if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream
            val payload = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            if (connection.responseCode !in 200..299) {
                throw ApiException(connection.responseCode, safeError(payload))
            }
            if (payload.isBlank()) JSONObject() else JSONObject(payload)
        } catch (error: ApiException) {
            throw error
        } catch (error: Exception) {
            throw IOException("Health Guardian service is unavailable", error)
        } finally {
            connection.disconnect()
        }
    }

    override fun askAssistant(userId: String, question: String): String {
        val latest = request("/api/v1/member3/insights?user_id=${encoded(userId)}")
            .arrayFrom("insights").optJSONObject(0)
            ?: return "I need a recent health insight before I can explain a personal change. Sync your health data and try again."
        val evidence = latest.optJSONArray("evidence") ?: JSONArray()
        if (evidence.length() == 0) return "The latest insight has no usable evidence, so I cannot safely explain it yet."
        val safetyAction = latest.optString("safety_action", "observe")
        val payload = JSONObject()
            .put("user_id", userId)
            .put("question", question)
            .put("evidence", evidence)
            .put("safety_action", safetyAction)
            .put("safety_reason", latest.optString("summary", "Based on your latest health insight"))
        val response = request("/api/v1/member3/assistant/explain", "POST", payload)
        return response.optString("answer", "No explanation returned")
    }

    override fun listInsights(userId: String): List<HealthInsight> {
        val response = request("/api/v1/member3/insights?user_id=${encoded(userId)}")
        return response.arrayFrom("insights", "items").mapObjects { item ->
            HealthInsight(
                id = item.optString("insight_id", item.optString("id")),
                title = item.optString("title", "Health insight"),
                summary = item.optString("summary", item.optString("message")),
                status = item.optString("status", "active"),
            )
        }
    }

    override fun listAlerts(userId: String): List<GuardianAlert> {
        val response = request("/api/v1/member3/alerts?user_id=${encoded(userId)}")
        return response.arrayFrom("alerts", "items").mapObjects { item ->
            GuardianAlert(
                id = item.optString("alert_id", item.optString("id")),
                title = item.optString("title", "Health alert"),
                message = item.optString("message"),
                priority = item.optString("priority", "normal"),
                status = item.optString("status", "active"),
            )
        }
    }

    override fun listCaregivers(userId: String): List<Caregiver> {
        val response = request("/api/v1/member3/caregivers?user_id=${encoded(userId)}")
        return response.arrayFrom("caregivers", "items", "links").mapObjects { item ->
            Caregiver(
                id = item.optString("link_id", item.optString("id")),
                name = item.optString("relationship_label", item.optString("caregiver_user_ref", "Caregiver")),
                status = item.optString("status", "pending"),
            )
        }
    }

    override fun inviteCaregiver(userId: String, caregiverUserRef: String, relationshipLabel: String): Caregiver {
        val payload = JSONObject()
            .put("user_id", userId)
            .put("caregiver_user_ref", caregiverUserRef)
            .put("relationship_label", relationshipLabel)
        val response = request("/api/v1/member3/caregivers", "POST", payload)
        return Caregiver(
            id = response.optString("link_id", response.optString("id")),
            name = response.optString("relationship_label", caregiverUserRef),
            status = response.optString("status", "pending"),
        )
    }

    override fun startEmergency(userId: String, reason: String): EmergencyWorkflow {
        val payload = JSONObject()
            .put("user_id", userId)
            .put("alert_id", "manual-${UUID.randomUUID()}")
            .put("safety_action", "emergency_escalation")
            .put("safety_reason", reason)
            .put("evidence", JSONArray().put("User manually reported urgent symptoms: $reason"))
        val response = request("/api/v1/member3/emergency/workflows", "POST", payload)
        return EmergencyWorkflow(
            id = response.optString("workflow_id", response.optString("id")),
            status = response.optString("state", "initiated"),
            nextAction = response.optString("urgent_instruction", "Confirm before contacting help"),
        )
    }

    private fun safeError(payload: String): String = runCatching {
        JSONObject(payload).optString("detail", "Request failed")
    }.getOrDefault("Request failed")

    private fun JSONObject.arrayFrom(vararg names: String): JSONArray {
        names.forEach { name -> optJSONArray(name)?.let { return it } }
        return JSONArray()
    }

    private fun encoded(value: String): String = URLEncoder.encode(value, StandardCharsets.UTF_8.toString())

    private fun <T> JSONArray.mapObjects(block: (JSONObject) -> T): List<T> =
        (0 until length()).map { block(getJSONObject(it)) }

    class ApiException(val status: Int, override val message: String) : IOException(message)
}
