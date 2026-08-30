package com.healthguardian.member3.data

data class AssistantMessage(val id: String, val text: String, val fromUser: Boolean)
data class HealthInsight(val id: String, val title: String, val summary: String, val status: String)
data class GuardianAlert(val id: String, val title: String, val message: String, val priority: String, val status: String)
data class Caregiver(val id: String, val name: String, val status: String)
data class EmergencyWorkflow(val id: String, val status: String, val nextAction: String)

sealed interface LoadState<out T> {
    data object Idle : LoadState<Nothing>
    data object Loading : LoadState<Nothing>
    data class Ready<T>(val value: T) : LoadState<T>
    data class Offline(val cached: Boolean, val message: String) : LoadState<Nothing>
    data class Error(val message: String) : LoadState<Nothing>
}
