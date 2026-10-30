package com.healthguardian.app.data.mapper

import com.healthguardian.app.data.remote.dto.*
import com.healthguardian.app.domain.model.*

fun UserResponse.toDomain(): User {
    return User(
        id = id,
        email = email,
        name = name,
        createdAt = created_at
    )
}

fun HealthProfileResponse.toDomain(): HealthProfile {
    return HealthProfile(
        userId = user_id,
        name = name,
        dateOfBirth = date_of_birth,
        sex = sex,
        height = height,
        weight = weight,
        bloodGroup = blood_group,
        allergies = allergies,
        medicalConditions = medical_conditions,
        medications = medications,
        updatedAt = updated_at
    )
}

fun HealthRecordResponse.toDomain(): HealthRecord {
    return HealthRecord(
        id = id,
        userId = user_id,
        type = type,
        title = title,
        description = description,
        date = date,
        value = value,
        unit = unit,
        createdAt = created_at
    )
}

fun ChatResponse.toDomain(): AIMessage {
    return AIMessage(
        id = id,
        conversationId = conversation_id,
        role = role,
        content = content,
        timestamp = timestamp,
        requiresUrgentAttention = requires_urgent_attention
    )
}

fun InsightResponse.toDomain(): HealthInsight {
    return HealthInsight(
        id = id,
        type = type,
        severity = severity,
        title = title,
        description = description,
        createdAt = created_at
    )
}

fun HealthMetricResponse.toDomain(): HealthMetric {
    return HealthMetric(
        type = type,
        value = value,
        unit = unit,
        timestamp = timestamp
    )
}