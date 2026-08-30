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
    val messages: List<AssistantMessage> = emptyList(),
    val assistantState: LoadState<Unit> = LoadState.Idle,
    val insights: LoadState<List<HealthInsight>> = LoadState.Idle,
    val alerts: LoadState<List<GuardianAlert>> = LoadState.Idle,
    val caregivers: LoadState<List<Caregiver>> = LoadState.Idle,
    val emergency: LoadState<EmergencyWorkflow> = LoadState.Idle,
)

class GuardianViewModel(private val repository: Member3Repository) : ViewModel() {
    private val userId = "demo-user" // Replace with authenticated identity during shared integration.
    private val _state = MutableStateFlow(GuardianUiState())
    val state: StateFlow<GuardianUiState> = _state.asStateFlow()

    fun refresh() {
        _state.value = _state.value.copy(insights = LoadState.Loading, alerts = LoadState.Loading, caregivers = LoadState.Loading)
        viewModelScope.launch(Dispatchers.IO) {
            val insights = repository.insights(userId)
            val alerts = repository.alerts(userId)
            val caregivers = apiState { repository.caregivers(userId) }
            _state.value = _state.value.copy(insights = insights, alerts = alerts, caregivers = caregivers)
        }
    }

    fun sendQuestion(question: String) {
        val clean = question.trim()
        if (clean.isEmpty() || _state.value.assistantState is LoadState.Loading) return
        val local = AssistantMessage(UUID.randomUUID().toString(), clean, true)
        _state.value = _state.value.copy(messages = _state.value.messages + local, assistantState = LoadState.Loading)
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val reply = repository.ask(userId, clean)
                _state.value = _state.value.copy(messages = _state.value.messages + reply, assistantState = LoadState.Ready(Unit))
            } catch (error: IOException) {
                _state.value = _state.value.copy(assistantState = LoadState.Offline(false, error.message ?: "Assistant unavailable"))
            } catch (error: Exception) {
                _state.value = _state.value.copy(assistantState = LoadState.Error(error.message ?: "Unable to answer"))
            }
        }
    }

    fun startEmergency(reason: String) {
        if (reason.isBlank()) return
        _state.value = _state.value.copy(emergency = LoadState.Loading)
        viewModelScope.launch(Dispatchers.IO) {
            _state.value = _state.value.copy(emergency = apiState { repository.startEmergency(userId, reason) })
        }
    }

    private fun <T> apiState(block: () -> T): LoadState<T> = try {
        LoadState.Ready(block())
    } catch (error: IOException) {
        LoadState.Offline(false, error.message ?: "Service unavailable")
    } catch (error: Exception) {
        LoadState.Error(error.message ?: "Unexpected error")
    }

    class Factory(private val repository: Member3Repository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = GuardianViewModel(repository) as T
    }
}
