package com.healthguardian.member3.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.healthguardian.member3.data.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.IOException
import java.util.UUID

data class GuardianUiState(
    val currentUserId: String = "",
    val isAuthenticated: Boolean = true,
    val messages: List<AssistantMessage> = emptyList(),
    val assistantState: LoadState<Unit> = LoadState.Idle,
    val insights: LoadState<List<HealthInsight>> = LoadState.Idle,
    val alerts: LoadState<List<GuardianAlert>> = LoadState.Idle,
    val caregivers: LoadState<List<Caregiver>> = LoadState.Idle,
    val emergency: LoadState<EmergencyWorkflow> = LoadState.Idle,
)

class GuardianViewModel(
    private val repository: Member3Repository,
    private val sessionManager: SessionManager = InMemorySessionManager(),
) : ViewModel() {
    val userId: String
        get() = sessionManager.currentUserId

    private val _state = MutableStateFlow(
        GuardianUiState(
            currentUserId = sessionManager.currentUserId,
            isAuthenticated = sessionManager.isAuthenticated,
        )
    )
    val state: StateFlow<GuardianUiState> = _state.asStateFlow()

    fun switchUser(newUserId: String, token: String? = null) {
        sessionManager.updateSession(newUserId, token)
        _state.value = _state.value.copy(
            currentUserId = sessionManager.currentUserId,
            isAuthenticated = sessionManager.isAuthenticated,
            messages = emptyList(),
        )
        refresh()
    }

    fun refresh() {
        if (!sessionManager.isAuthenticated) {
            _state.value = _state.value.copy(
                insights = LoadState.Error("Please log in to view health data"),
                alerts = LoadState.Error("Please log in to view alerts"),
                caregivers = LoadState.Error("Please log in to view caregivers"),
            )
            return
        }
        _state.value = _state.value.copy(
            insights = LoadState.Loading,
            alerts = LoadState.Loading,
            caregivers = LoadState.Loading,
        )
        viewModelScope.launch(Dispatchers.IO) {
            val insights = repository.insights(userId)
            val alerts = repository.alerts(userId)
            val caregivers = repository.caregivers(userId)
            _state.value = _state.value.copy(
                insights = insights,
                alerts = alerts,
                caregivers = caregivers,
            )
        }
    }

    fun sendQuestion(question: String) {
        val clean = question.trim()
        if (clean.isEmpty() || _state.value.assistantState is LoadState.Loading) return
        val local = AssistantMessage(UUID.randomUUID().toString(), clean, true)
        _state.value = _state.value.copy(
            messages = _state.value.messages + local,
            assistantState = LoadState.Loading,
        )
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val reply = repository.ask(userId, clean)
                _state.value = _state.value.copy(
                    messages = _state.value.messages + reply,
                    assistantState = LoadState.Ready(Unit),
                )
            } catch (error: IOException) {
                _state.value = _state.value.copy(
                    assistantState = LoadState.Offline(false, error.message ?: "Assistant unavailable"),
                )
            } catch (error: Exception) {
                _state.value = _state.value.copy(
                    assistantState = LoadState.Error(error.message ?: "Unable to answer"),
                )
            }
        }
    }

    fun inviteCaregiver(caregiverRef: String, label: String) {
        if (caregiverRef.isBlank() || label.isBlank()) return
        viewModelScope.launch(Dispatchers.IO) {
            try {
                repository.inviteCaregiver(userId, caregiverRef.trim(), label.trim())
                val updatedCaregivers = repository.caregivers(userId)
                _state.value = _state.value.copy(caregivers = updatedCaregivers)
            } catch (error: Exception) {
                _state.value = _state.value.copy(
                    caregivers = LoadState.Error(error.message ?: "Failed to invite caregiver"),
                )
            }
        }
    }

    fun startEmergency(reason: String) {
        if (reason.isBlank()) return
        _state.value = _state.value.copy(emergency = LoadState.Loading)
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val workflow = repository.startEmergency(userId, reason)
                _state.value = _state.value.copy(emergency = LoadState.Ready(workflow))
            } catch (error: IOException) {
                _state.value = _state.value.copy(
                    emergency = LoadState.Offline(false, error.message ?: "Emergency service offline"),
                )
            } catch (error: Exception) {
                _state.value = _state.value.copy(
                    emergency = LoadState.Error(error.message ?: "Unable to start emergency workflow"),
                )
            }
        }
    }

    class Factory(
        private val repository: Member3Repository,
        private val sessionManager: SessionManager = InMemorySessionManager(),
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            GuardianViewModel(repository, sessionManager) as T
    }
}
