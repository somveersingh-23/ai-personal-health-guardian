package com.healthguardian.app.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.healthguardian.app.data.local.DigitalTwinLocalDataSource
import com.healthguardian.app.data.repository.DigitalTwinRepositoryImpl
import com.healthguardian.app.domain.model.DigitalTwin
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface DigitalTwinUiState {

    data object Loading : DigitalTwinUiState

    data class Success(
        val digitalTwin: DigitalTwin
    ) : DigitalTwinUiState

    data class Error(
        val message: String
    ) : DigitalTwinUiState

    data object Empty : DigitalTwinUiState
}

class DigitalTwinViewModel : ViewModel() {

    private val repository = DigitalTwinRepositoryImpl(
        DigitalTwinLocalDataSource()
    )

    private val _uiState =
        MutableStateFlow<DigitalTwinUiState>(DigitalTwinUiState.Loading)

    val uiState: StateFlow<DigitalTwinUiState> =
        _uiState.asStateFlow()

    init {
        loadDigitalTwin()
    }

    fun loadDigitalTwin() {
        viewModelScope.launch {

            _uiState.value = DigitalTwinUiState.Loading

            try {

                val digitalTwin = repository.getDigitalTwin()

                if (
                    digitalTwin.currentMetrics.isEmpty() &&
                    digitalTwin.profile == null
                ) {
                    _uiState.value = DigitalTwinUiState.Empty
                } else {
                    _uiState.value =
                        DigitalTwinUiState.Success(digitalTwin)
                }

            } catch (exception: Exception) {

                _uiState.value =
                    DigitalTwinUiState.Error(
                        exception.message
                            ?: "Unable to load health data."
                    )
            }
        }
    }
}