package com.healthguardian.member3.data

import java.io.IOException
import java.util.UUID

class Member3Repository(private val api: Member3ApiClient) {
    private val cachedInsights = mutableListOf<HealthInsight>()
    private val cachedAlerts = mutableListOf<GuardianAlert>()

    fun ask(userId: String, question: String): AssistantMessage =
        AssistantMessage(UUID.randomUUID().toString(), api.askAssistant(userId, question), false)

    fun insights(userId: String): LoadState<List<HealthInsight>> = cachedRequest(cachedInsights) {
        api.listInsights(userId)
    }

    fun alerts(userId: String): LoadState<List<GuardianAlert>> = cachedRequest(cachedAlerts) {
        api.listAlerts(userId)
    }

    fun caregivers(userId: String): List<Caregiver> = api.listCaregivers(userId)
    fun startEmergency(userId: String, reason: String): EmergencyWorkflow = api.startEmergency(userId, reason)

    private fun <T> cachedRequest(cache: MutableList<T>, fetch: () -> List<T>): LoadState<List<T>> = try {
        val latest = fetch()
        cache.clear()
        cache.addAll(latest)
        LoadState.Ready(latest)
    } catch (error: IOException) {
        LoadState.Offline(cache.isNotEmpty(), error.message ?: "You appear to be offline")
    } catch (error: Exception) {
        LoadState.Error(error.message ?: "Unexpected error")
    }
}
