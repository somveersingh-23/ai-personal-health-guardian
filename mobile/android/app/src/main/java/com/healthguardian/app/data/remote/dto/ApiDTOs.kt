package com.healthguardian.app.data.remote.dto

import kotlinx.serialization.Serializable

// Auth
@Serializable
data class LoginRequest(
    val email: String,
    val password: String
)

@Serializable
data class RegisterRequest(
    val email: String,
    val password: String,
    val name: String? = null
)

@Serializable
data class AuthResponse(
    val access_token: String,
    val refresh_token: String?,
    val token_type: String = "Bearer",
    val expires_in: Int? = null,
    val user: UserResponse?
)

@Serializable
data class UserResponse(
    val id: String,
    val email: String,
    val name: String?,
    val created_at: String,
    val last_login_at: String?
)

// Health Profile
@Serializable
data class HealthProfileResponse(
    val user_id: String,
    val name: String,
    val date_of_birth: String?,
    val sex: String?,
    val height: Double?,
    val weight: Double?,
    val blood_group: String?,
    val allergies: List<String>,
    val medical_conditions: List<String>,
    val medications: List<String>,
    val updated_at: String
)

@Serializable
data class HealthProfileRequest(
    val name: String,
    val date_of_birth: String?,
    val sex: String?,
    val height: Double?,
    val weight: Double?,
    val blood_group: String?,
    val allergies: List<String> = emptyList(),
    val medical_conditions: List<String> = emptyList(),
    val medications: List<String> = emptyList()
)

// Health Records
@Serializable
data class HealthRecordResponse(
    val id: String,
    val user_id: String,
    val type: String,
    val title: String,
    val description: String?,
    val date: String,
    val value: Double?,
    val unit: String?,
    val created_at: String
)

@Serializable
data class HealthRecordRequest(
    val type: String,
    val title: String,
    val description: String?,
    val date: String,
    val value: Double?,
    val unit: String?
)

// AI Chat
@Serializable
data class ChatRequest(
    val message: String,
    val conversation_id: String? = null
)

@Serializable
data class ChatResponse(
    val id: String,
    val conversation_id: String,
    val role: String,
    val content: String,
    val timestamp: String,
    val requires_urgent_attention: Boolean = false
)

// Insights
@Serializable
data class InsightResponse(
    val id: String,
    val type: String,
    val severity: String,
    val title: String,
    val description: String,
    val created_at: String
)

// Dashboard
@Serializable
data class DashboardResponse(
    val user_name: String,
    val health_metrics: List<HealthMetricResponse>,
    val recent_records: List<HealthRecordResponse>,
    val recent_insights: List<InsightResponse>,
    val profile_completion_percentage: Int
)

@Serializable
data class HealthMetricResponse(
    val type: String,
    val value: Double,
    val unit: String,
    val timestamp: String
)