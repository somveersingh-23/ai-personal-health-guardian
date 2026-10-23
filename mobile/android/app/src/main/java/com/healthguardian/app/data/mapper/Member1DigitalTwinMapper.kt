package com.healthguardian.app.data.mapper

import com.healthguardian.app.data.remote.dto.Member1DigitalTwinResponse
import com.healthguardian.app.domain.model.BaselineStatus
import com.healthguardian.app.domain.model.DigitalTwin
import com.healthguardian.app.domain.model.HealthBaseline
import com.healthguardian.app.domain.model.HealthDeviation
import com.healthguardian.app.domain.model.HealthEvent
import com.healthguardian.app.domain.model.HealthMetric
import com.healthguardian.app.domain.model.HealthState
import com.healthguardian.app.domain.model.HealthTrend
import com.healthguardian.app.domain.model.TrendDirection

fun Member1DigitalTwinResponse.toDomain(): DigitalTwin {
    val metricByType = current_metrics.associateBy { it.type }
    val baselinesDomain = baselines.map { baseline ->
        val current = metricByType[baseline.event_type]?.value
        val status = when {
            current == null -> BaselineStatus.UNKNOWN
            current < baseline.lower_bound -> BaselineStatus.BELOW_NORMAL
            current > baseline.upper_bound -> BaselineStatus.ABOVE_NORMAL
            else -> BaselineStatus.NORMAL
        }
        val z = if (baseline.std > 0 && current != null) {
            (current - baseline.mean) / baseline.std
        } else {
            null
        }
        HealthBaseline(
            metricType = baseline.event_type.toReadableMetric(),
            baselineValue = baseline.mean,
            unit = metricByType[baseline.event_type]?.unit.orEmpty(),
            currentValue = current,
            deviationScore = z,
            status = status
        )
    }

    val trendsDomain = trends.map { trend ->
        HealthTrend(
            metricType = trend.metric_type.toReadableMetric(),
            direction = when (trend.direction.lowercase()) {
                "increasing", "improving" -> TrendDirection.IMPROVING
                "decreasing", "declining" -> TrendDirection.DECLINING
                "stable" -> TrendDirection.STABLE
                else -> TrendDirection.UNKNOWN
            },
            changePercentage = trend.change_percentage,
            period = trend.period,
            description = null
        )
    }

    val deviationsDomain = anomalies.map { anomaly ->
        val baseline = baselines.firstOrNull { it.event_type == anomaly.event_type }
        val current = anomaly.value
        val status = when {
            current == null || baseline == null -> BaselineStatus.UNKNOWN
            current < baseline.lower_bound -> BaselineStatus.BELOW_NORMAL
            current > baseline.upper_bound -> BaselineStatus.ABOVE_NORMAL
            else -> BaselineStatus.NORMAL
        }
        HealthDeviation(
            metricType = anomaly.event_type.toReadableMetric(),
            currentValue = current,
            baselineValue = baseline?.mean,
            deviationScore = null,
            status = status,
            description = anomaly.explanation.ifBlank { anomaly.severity }
        )
    }

    val recentEventsDomain = recent_events.mapIndexed { index, event ->
        HealthEvent(
            id = (event.event_id ?: event.id ?: index).toString(),
            metricType = event.event_type.toReadableMetric(),
            value = event.value,
            unit = event.unit,
            timestamp = event.event_time,
            source = event.source,
            quality = "synthetic_or_recorded"
        )
    }

    val overall = when (state.lowercase()) {
        "stable" -> HealthState.STABLE
        "improving" -> HealthState.IMPROVING
        "watch", "elevated", "attention_required" -> HealthState.NEEDS_ATTENTION
        else -> HealthState.UNKNOWN
    }

    return DigitalTwin(
        profile = null,
        currentMetrics = current_metrics.map {
            HealthMetric(
                type = it.type.toReadableMetric(),
                value = it.value,
                unit = it.unit,
                timestamp = it.timestamp
            )
        },
        baselines = baselinesDomain,
        trends = trendsDomain,
        deviations = deviationsDomain,
        recentEvents = recentEventsDomain,
        overallState = overall
    )
}

private fun String.toReadableMetric(): String = replace('_', ' ')
    .split(' ')
    .filter { it.isNotBlank() }
    .joinToString(" ") { token -> token.replaceFirstChar { it.uppercase() } }
