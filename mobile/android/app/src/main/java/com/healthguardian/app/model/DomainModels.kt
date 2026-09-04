package com.healthguardian.app.domain.model

data class User(
    val id: String,
    val email: String,
    val name: String?,
    val createdAt: String
)

data class HealthProfile(
    val userId: String,
    val name: String,
    val dateOfBirth: String?,
    val sex: String?,
    val height: Double?,
    val weight: Double?,
    val bloodGroup: String?,
    val allergies: List<String>,
    val medicalConditions: List<String>,
    val medications: List<String>,
    val updatedAt: String
)

data class HealthRecord(
    val id: String,
    val userId: String,
    val type: String,
    val title: String,
    val description: String?,
    val date: String,
    val value: Double?,
    val unit: String?,
    val createdAt: String
)

data class AIMessage(
    val id: String,
    val conversationId: String,
    val role: String,
    val content: String,
    val timestamp: String,
    val requiresUrgentAttention: Boolean
)

data class HealthInsight(
    val id: String,
    val type: String,
    val severity: String,
    val title: String,
    val description: String,
    val createdAt: String
)

data class HealthMetric(
    val type: String,
    val value: Double,
    val unit: String,
    val timestamp: String
)