package com.healthguardian.member3.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

interface LocalGuardianCache {
    fun getInsights(userId: String): List<HealthInsight>
    fun saveInsights(userId: String, insights: List<HealthInsight>)
    fun getAlerts(userId: String): List<GuardianAlert>
    fun saveAlerts(userId: String, alerts: List<GuardianAlert>)
    fun clear(userId: String)
}

class InMemoryGuardianCache : LocalGuardianCache {
    private val insightsCache = mutableMapOf<String, List<HealthInsight>>()
    private val alertsCache = mutableMapOf<String, List<GuardianAlert>>()

    override fun getInsights(userId: String): List<HealthInsight> =
        insightsCache[userId].orEmpty()

    override fun saveInsights(userId: String, insights: List<HealthInsight>) {
        insightsCache[userId] = insights
    }

    override fun getAlerts(userId: String): List<GuardianAlert> =
        alertsCache[userId].orEmpty()

    override fun saveAlerts(userId: String, alerts: List<GuardianAlert>) {
        alertsCache[userId] = alerts
    }

    override fun clear(userId: String) {
        insightsCache.remove(userId)
        alertsCache.remove(userId)
    }
}

/** App-private durable cache. Authentication tokens are deliberately excluded. */
class PreferencesGuardianCache(context: Context) : LocalGuardianCache {
    private val preferences = context.applicationContext.getSharedPreferences(
        "member3_guardian_cache_v1",
        Context.MODE_PRIVATE,
    )

    override fun getInsights(userId: String): List<HealthInsight> =
        readArray("insights", userId).map { item ->
            HealthInsight(
                id = item.getString("id"),
                title = item.getString("title"),
                summary = item.getString("summary"),
                status = item.getString("status"),
            )
        }

    override fun saveInsights(userId: String, insights: List<HealthInsight>) {
        val array = JSONArray()
        insights.forEach { item ->
            array.put(JSONObject().apply {
                put("id", item.id); put("title", item.title)
                put("summary", item.summary); put("status", item.status)
            })
        }
        writeArray("insights", userId, array)
    }

    override fun getAlerts(userId: String): List<GuardianAlert> =
        readArray("alerts", userId).map { item ->
            GuardianAlert(
                id = item.getString("id"),
                title = item.getString("title"),
                message = item.getString("message"),
                priority = item.getString("priority"),
                status = item.getString("status"),
            )
        }

    override fun saveAlerts(userId: String, alerts: List<GuardianAlert>) {
        val array = JSONArray()
        alerts.forEach { item ->
            array.put(JSONObject().apply {
                put("id", item.id); put("title", item.title); put("message", item.message)
                put("priority", item.priority); put("status", item.status)
            })
        }
        writeArray("alerts", userId, array)
    }

    override fun clear(userId: String) {
        preferences.edit()
            .remove(key("insights", userId))
            .remove(key("alerts", userId))
            .apply()
    }

    private fun readArray(type: String, userId: String): List<JSONObject> {
        return try {
            val raw = preferences.getString(key(type, userId), null) ?: return emptyList()
            val array = JSONArray(raw)
            List(array.length()) { index -> array.getJSONObject(index) }
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun writeArray(type: String, userId: String, array: JSONArray) {
        preferences.edit().putString(key(type, userId), array.toString()).apply()
    }

    private fun key(type: String, userId: String): String =
        "$type:${userId.trim().hashCode()}"
}
