package com.healthguardian.app.core.ui

/**
 * Base interface for UI states with loading and error handling
 */
interface BaseUiState {
    val isLoading: Boolean
    val error: UiText?
}

/**
 * Base interface for UI events
 */
interface BaseEvent

/**
 * Generic loading state implementation
 */
data class LoadingUiState(
    override val isLoading: Boolean = true,
    override val error: UiText? = null
) : BaseUiState

/**
 * Generic error state implementation
 */
data class ErrorUiState(
    override val isLoading: Boolean = false,
    override val error: UiText
) : BaseUiState

/**
 * Generic success state with data
 */
data class SuccessUiState<T>(
    val data: T,
    override val isLoading: Boolean = false,
    override val error: UiText? = null
) : BaseUiState

/**
 * Generic data state with loading, error, and success
 */
sealed class UiState<out T> : BaseUiState {
    object Loading : UiState<Nothing>() {
        override val isLoading: Boolean = true
        override val error: UiText? = null
    }

    data class Success<T>(val data: T) : UiState<T>() {
        override val isLoading: Boolean = false
        override val error: UiText? = null
    }

    data class Error(override val error: UiText) : UiState<Nothing>() {
        override val isLoading: Boolean = false
    }
}

/**
 * Get data from state or null
 */
fun <T> UiState<T>.dataOrNull(): T? {
    return when (this) {
        is UiState.Success -> data
        else -> null
    }
}

/**
 * Check if state is loading
 */
fun <T> UiState<T>.isLoading(): Boolean {
    return this is UiState.Loading
}

/**
 * Check if state is error
 */
fun <T> UiState<T>.isError(): Boolean {
    return this is UiState.Error
}

/**
 * Check if state is success
 */
fun <T> UiState<T>.isSuccess(): Boolean {
    return this is UiState.Success
}