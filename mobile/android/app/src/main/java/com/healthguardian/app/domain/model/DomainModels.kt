package com.healthguardian.app.domain.model

// ============================================================
// USER
// ============================================================

data class User(
    val id: String,
    val email: String,
    val name: String?,
    val createdAt: String
)

// ============================================================
// HEALTH PROFILE
// ============================================================

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

// ============================================================
// HEALTH RECORD
// ============================================================

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

// ============================================================
// AI MESSAGE
// ============================================================

data class AIMessage(
    val id: String,
    val conversationId: String,
    val role: String,
    val content: String,
    val timestamp: String,
    val requiresUrgentAttention: Boolean
)

// ============================================================
// HEALTH INSIGHT
// ============================================================

data class HealthInsight(
    val id: String,
    val type: String,
    val severity: String,
    val title: String,
    val description: String,
    val createdAt: String
)

// ============================================================
// HEALTH METRIC
// ============================================================

data class HealthMetric(
    val type: String,
    val value: Double,
    val unit: String,
    val timestamp: String
)

// ============================================================
// PERSONAL HEALTH DIGITAL TWIN
// ============================================================

data class DigitalTwin(
    val profile: HealthProfile?,
    val currentMetrics: List<HealthMetric>,
    val baselines: List<HealthBaseline>,
    val trends: List<HealthTrend>,
    val deviations: List<HealthDeviation>,
    val recentEvents: List<HealthEvent>,
    val overallState: HealthState
)

// ============================================================
// HEALTH BASELINE
// ============================================================

data class HealthBaseline(
    val metricType: String,
    val baselineValue: Double,
    val unit: String,
    val currentValue: Double?,
    val deviationScore: Double?,
    val status: BaselineStatus
)

// ============================================================
// BASELINE STATUS
// ============================================================

enum class BaselineStatus {
    NORMAL,
    BELOW_NORMAL,
    ABOVE_NORMAL,
    UNKNOWN
}

// ============================================================
// HEALTH TREND
// ============================================================

data class HealthTrend(
    val metricType: String,
    val direction: TrendDirection,
    val changePercentage: Double?,
    val period: String,
    val description: String?
)

// ============================================================
// TREND DIRECTION
// ============================================================

enum class TrendDirection {
    IMPROVING,
    DECLINING,
    STABLE,
    UNKNOWN
}

// ============================================================
// HEALTH DEVIATION
// ============================================================

data class HealthDeviation(
    val metricType: String,
    val currentValue: Double?,
    val baselineValue: Double?,
    val deviationScore: Double?,
    val status: BaselineStatus,
    val description: String?
)

// ============================================================
// HEALTH EVENT
// ============================================================

data class HealthEvent(
    val id: String,
    val metricType: String,
    val value: Double?,
    val unit: String?,
    val timestamp: String,
    val source: String,
    val quality: String
)

// ============================================================
// OVERALL HEALTH STATE
// ============================================================

enum class HealthState {
    STABLE,
    IMPROVING,
    NEEDS_ATTENTION,
    UNKNOWN
}