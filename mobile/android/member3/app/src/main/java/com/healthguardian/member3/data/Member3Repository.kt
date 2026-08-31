package com.healthguardian.member3.data

import java.io.IOException
import java.util.UUID

class Member3Repository(
    private val api: Member3Gateway,
    private val cache: LocalGuardianCache = InMemoryGuardianCache(),
) {
    fun ask(userId: String, question: String): AssistantMessage =
        AssistantMessage(UUID.randomUUID().toString(), api.askAssistant(userId, question), false)

    fun insights(userId: String): LoadState<List<HealthInsight>> = try {
        val latest = api.listInsights(userId)
        cache.saveInsights(userId, latest)
        LoadState.Ready(latest)
    } catch (error: IOException) {
        val cached = cache.getInsights(userId)
        if (cached.isNotEmpty()) {
            LoadState.Offline(true, "Showing saved insights while offline")
        } else {
            LoadState.Offline(false, error.message ?: "You appear to be offline")
        }
    } catch (error: Exception) {
        LoadState.Error(error.message ?: "Unexpected error")
    }

    fun alerts(userId: String): LoadState<List<GuardianAlert>> = try {
        val latest = api.listAlerts(userId)
        cache.saveAlerts(userId, latest)
        LoadState.Ready(latest)
    } catch (error: IOException) {
        val cached = cache.getAlerts(userId)
        if (cached.isNotEmpty()) {
            LoadState.Offline(true, "Showing saved alerts while offline")
        } else {
            LoadState.Offline(false, error.message ?: "You appear to be offline")
        }
    } catch (error: Exception) {
        LoadState.Error(error.message ?: "Unexpected error")
    }

    fun caregivers(userId: String): LoadState<List<Caregiver>> = try {
        val latest = api.listCaregivers(userId)
        LoadState.Ready(latest)
    } catch (error: IOException) {
        LoadState.Offline(false, error.message ?: "Caregivers unavailable while offline")
    } catch (error: Exception) {
        LoadState.Error(error.message ?: "Unable to load caregivers")
    }

    fun inviteCaregiver(userId: String, caregiverRef: String, label: String): Caregiver =
        api.inviteCaregiver(userId, caregiverRef, label)

    fun startEmergency(userId: String, reason: String): EmergencyWorkflow =
        api.startEmergency(userId, reason)
}
