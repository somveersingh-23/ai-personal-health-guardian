package com.healthguardian.app.data.remote.dto

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
data class Member1MetricDTO(
    val type: String = "",
    val value: Double = 0.0,
    val unit: String = "",
    val timestamp: String = ""
)

@Serializable
data class Member1BaselineDTO(
    val event_type: String = "",
    val mean: Double = 0.0,
    val std: Double = 0.0,
    val lower_bound: Double = 0.0,
    val upper_bound: Double = 0.0,
    val baseline_quality: String = "unknown"
)

@Serializable
data class Member1TrendDTO(
    val metric_type: String = "",
    val direction: String = "unknown",
    val change_percentage: Double? = null,
    val period: String = "",
)

@Serializable
data class Member1AnomalyDTO(
    val event_id: Int? = null,
    val event_type: String = "",
    val value: Double? = null,
    val unit: String? = null,
    val event_time: String = "",
    val severity: String = "low",
    val confidence: Double = 0.0,
    val explanation: String = "",
)

@Serializable
data class Member1HealthEventDTO(
    val event_id: Int? = null,
    val id: Int? = null,
    val event_type: String = "",
    val value: Double? = null,
    val unit: String? = null,
    val event_time: String = "",
    val source: String = "ml_pipeline",
)

@Serializable
data class Member1DigitalTwinResponse(
    val user_id: Int,
    val generated_at: String = "",
    val latest_event_time: String? = null,
    val state: String = "no_data",
    val anomaly_score: Double = 0.0,
    val summary: Map<String, Double> = emptyMap(),
    val current_metrics: List<Member1MetricDTO> = emptyList(),
    val vitals: Map<String, Member1MetricDTO> = emptyMap(),
    val lifestyle: Map<String, Member1MetricDTO> = emptyMap(),
    val baselines: List<Member1BaselineDTO> = emptyList(),
    val trends: List<Member1TrendDTO> = emptyList(),
    val anomalies: List<Member1AnomalyDTO> = emptyList(),
    val recent_events: List<Member1HealthEventDTO> = emptyList(),
)

@Serializable
data class Member1HealthInsightDTO(
    val insight_id: String = "",
    val generated_at: String = "",
    val insight_type: String = "",
    val category: String = "",
    val severity: String = "low",
    val priority: Int = 0,
    val confidence: Double = 0.0,
    val title: String = "",
    val message: String = "",
    val recommended_action: String = "",
    val supporting_data: Map<String, JsonElement> = emptyMap(),
)

@Serializable
data class Member1HealthIntelligenceResponse(
    val user_id: Int,
    val generated_at: String = "",
    val digital_twin_state: String = "no_data",
    val anomaly_score: Double = 0.0,
    val insight_count: Int = 0,
    val insights: List<Member1HealthInsightDTO> = emptyList(),
)
