package com.healthguardian.member3.data

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
