package com.healthguardian.app.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.healthguardian.app.core.common.Result
import com.healthguardian.app.core.common.runCatchingSuspend
import com.healthguardian.app.core.security.SecureTokenStore
import com.healthguardian.app.data.remote.api.ApiService
import com.healthguardian.app.data.remote.dto.LoginRequest
import com.healthguardian.app.data.remote.dto.RegisterRequest
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val apiService: ApiService,
    private val secureTokenStore: SecureTokenStore
) : ViewModel() {

    private val _authState = MutableStateFlow<AuthState>(AuthState.Loading)
    val authState: StateFlow<AuthState> = _authState.asStateFlow()

    init {
        checkAuthStatus()
    }

    private fun checkAuthStatus() {
        viewModelScope.launch {
            _authState.value = AuthState.Loading

            val isAuthenticated = secureTokenStore.isAuthenticated()
            _authState.value = if (isAuthenticated) {
                AuthState.Authenticated
            } else {
                AuthState.Unauthenticated
            }
        }
    }

    fun login(email: String, password: String, onComplete: (Result<Unit>) -> Unit) {
        viewModelScope.launch {
            _authState.value = AuthState.Loading

            val result = runCatchingSuspend {
                val response = apiService.login(LoginRequest(email, password))

                if (response.isSuccessful && response.body() != null) {
                    val authResponse = response.body()!!

                    secureTokenStore.saveTokens(
                        accessToken = authResponse.access_token,
                        refreshToken = authResponse.refresh_token,
                        expiryTimestamp = authResponse.expires_in?.let {
                            System.currentTimeMillis() + (it * 1000L)
                        }
                    )

                    _authState.value = AuthState.Authenticated
                    Unit
                } else {
                    val errorMessage = when (response.code()) {
                        401 -> "Invalid email or password"
                        500 -> "Server error. Please try again later"
                        else -> response.message().ifBlank { "Login failed" }
                    }
                    throw Exception(errorMessage)
                }
            }

            onComplete(result)
        }
    }

    fun register(
        email: String,
        password: String,
        name: String?,
        onComplete: (Result<Unit>) -> Unit
    ) {
        viewModelScope.launch {
            _authState.value = AuthState.Loading

            val result = runCatchingSuspend {
                val response = apiService.register(
                    RegisterRequest(email, password, name)
                )

                if (response.isSuccessful && response.body() != null) {
                    val authResponse = response.body()!!

                    secureTokenStore.saveTokens(
                        accessToken = authResponse.access_token,
                        refreshToken = authResponse.refresh_token,
                        expiryTimestamp = authResponse.expires_in?.let {
                            System.currentTimeMillis() + (it * 1000L)
                        }
                    )

                    _authState.value = AuthState.Authenticated
                    Unit
                } else {
                    val errorMessage = when (response.code()) {
                        400 -> "Invalid registration data"
                        409 -> "Email already registered"
                        500 -> "Server error. Please try again later"
                        else -> response.message().ifBlank { "Registration failed" }
                    }
                    throw Exception(errorMessage)
                }
            }

            onComplete(result)
        }
    }

    fun logout(onComplete: () -> Unit) {
        viewModelScope.launch {
            secureTokenStore.clearTokens()
            _authState.value = AuthState.Unauthenticated
            onComplete()
        }
    }

    sealed class AuthState {
        object Loading : AuthState()
        object Authenticated : AuthState()
        object Unauthenticated : AuthState()
    }
}