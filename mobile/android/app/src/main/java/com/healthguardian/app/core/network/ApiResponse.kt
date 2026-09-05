package com.healthguardian.app.core.network

sealed class ApiResponse<out T> {
    object Loading : ApiResponse<Nothing>()
    data class Success<out T>(val data: T) : ApiResponse<T>()
    data class Error(val message: String, val code: Int? = null) : ApiResponse<Nothing>()
}

fun <T, R> ApiResponse<T>.map(transform: (T) -> R): ApiResponse<R> {
    return when (this) {
        is ApiResponse.Loading -> ApiResponse.Loading
        is ApiResponse.Success -> ApiResponse.Success(transform(data))
        is ApiResponse.Error -> this
    }
}

fun <T> ApiResponse<T>.getOrNull(): T? {
    return when (this) {
        is ApiResponse.Success -> data
        else -> null
    }
}