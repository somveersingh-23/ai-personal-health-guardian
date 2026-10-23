package com.healthguardian.app.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.healthguardian.app.data.repository.DigitalTwinRepositoryImpl
import com.healthguardian.app.domain.model.DigitalTwin
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface DigitalTwinUiState {
    data object Loading : DigitalTwinUiState
    data class Success(val digitalTwin: DigitalTwin) : DigitalTwinUiState
    data class Error(val message: String) : DigitalTwinUiState
    data object Empty : DigitalTwinUiState
}

@HiltViewModel
class DigitalTwinViewModel @Inject constructor(
    private val repository: DigitalTwinRepositoryImpl
) : ViewModel() {

    private val _uiState = MutableStateFlow<DigitalTwinUiState>(DigitalTwinUiState.Loading)
    val uiState: StateFlow<DigitalTwinUiState> = _uiState.asStateFlow()

    private var currentUserId: Int = 1

    fun loadDigitalTwin() {
        loadDigitalTwin(currentUserId)
    }

    fun loadDigitalTwin(userId: Int) {
        currentUserId = userId
        viewModelScope.launch {
            _uiState.value = DigitalTwinUiState.Loading
            try {
                val digitalTwin = repository.getDigitalTwin(userId)
                _uiState.value = if (
                    digitalTwin.currentMetrics.isEmpty() &&
                    digitalTwin.baselines.isEmpty() &&
                    digitalTwin.recentEvents.isEmpty()
                ) {
                    DigitalTwinUiState.Empty
                } else {
                    DigitalTwinUiState.Success(digitalTwin)
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (exception: Exception) {
                _uiState.value = DigitalTwinUiState.Error(
                    exception.message?.takeIf { it.isNotBlank() }
                        ?: "Unable to load health data. Check the connection and try again."
                )
            }
        }
    }
}
