package com.healthguardian.app.data.local

import com.healthguardian.app.domain.model.BaselineStatus
import com.healthguardian.app.domain.model.DigitalTwin
import com.healthguardian.app.domain.model.HealthBaseline
import com.healthguardian.app.domain.model.HealthDeviation
import com.healthguardian.app.domain.model.HealthEvent
import com.healthguardian.app.domain.model.HealthMetric
import com.healthguardian.app.domain.model.HealthProfile
import com.healthguardian.app.domain.model.HealthState
import com.healthguardian.app.domain.model.HealthTrend
import com.healthguardian.app.domain.model.TrendDirection

class DigitalTwinLocalDataSource {

    fun getDigitalTwin(): DigitalTwin {

        // ========================================================
        // HEALTH PROFILE
        // ========================================================

        val profile = HealthProfile(
            userId = "demo-user-001",
            name = "Demo User",
            dateOfBirth = "2003-12-13",
            sex = "Not specified",
            height = 165.0,
            weight = 70.0,
            bloodGroup = null,
            allergies = emptyList(),
            medicalConditions = emptyList(),
            medications = emptyList(),
            updatedAt = "2026-09-06T09:00:00"
        )

        // ========================================================
        // CURRENT HEALTH METRICS
        // ========================================================

        val currentMetrics = listOf(

            HealthMetric(
                type = "Heart Rate",
                value = 72.0,
                unit = "bpm",
                timestamp = "2026-09-06T09:42:00"
            ),

            HealthMetric(
                type = "Sleep",
                value = 7.5,
                unit = "hours",
                timestamp = "2026-09-06T07:30:00"
            ),

            HealthMetric(
                type = "Steps",
                value = 8432.0,
                unit = "steps",
                timestamp = "2026-09-06T14:30:00"
            ),

            HealthMetric(
                type = "Weight",
                value = 70.0,
                unit = "kg",
                timestamp = "2026-09-06T08:00:00"
            )
        )

        // ========================================================
        // PERSONAL BASELINES
        // ========================================================

        val baselines = listOf(

            HealthBaseline(
                metricType = "Heart Rate",
                baselineValue = 74.0,
                unit = "bpm",
                currentValue = 72.0,
                deviationScore = -0.15,
                status = BaselineStatus.NORMAL
            ),

            HealthBaseline(
                metricType = "Sleep",
                baselineValue = 7.2,
                unit = "hours",
                currentValue = 7.5,
                deviationScore = 0.12,
                status = BaselineStatus.NORMAL
            ),

            HealthBaseline(
                metricType = "Steps",
                baselineValue = 7500.0,
                unit = "steps",
                currentValue = 8432.0,
                deviationScore = 0.35,
                status = BaselineStatus.ABOVE_NORMAL
            ),

            HealthBaseline(
                metricType = "Weight",
                baselineValue = 69.5,
                unit = "kg",
                currentValue = 70.0,
                deviationScore = 0.08,
                status = BaselineStatus.NORMAL
            )
        )

        // ========================================================
        // HEALTH TRENDS
        // ========================================================

        val trends = listOf(

            HealthTrend(
                metricType = "Heart Rate",
                direction = TrendDirection.STABLE,
                changePercentage = -2.7,
                period = "7 days",
                description = "Heart rate has remained relatively stable."
            ),

            HealthTrend(
                metricType = "Sleep",
                direction = TrendDirection.IMPROVING,
                changePercentage = 4.2,
                period = "7 days",
                description = "Average sleep duration has slightly improved."
            ),

            HealthTrend(
                metricType = "Steps",
                direction = TrendDirection.IMPROVING,
                changePercentage = 12.4,
                period = "7 days",
                description = "Daily activity has increased compared with your baseline."
            ),

            HealthTrend(
                metricType = "Weight",
                direction = TrendDirection.STABLE,
                changePercentage = 0.7,
                period = "30 days",
                description = "Weight has remained relatively stable."
            )
        )

        // ========================================================
        // HEALTH DEVIATIONS
        // ========================================================

        val deviations = listOf(

            HealthDeviation(
                metricType = "Heart Rate",
                currentValue = 72.0,
                baselineValue = 74.0,
                deviationScore = -0.15,
                status = BaselineStatus.NORMAL,
                description = "Current heart rate is close to your personal baseline."
            ),

            HealthDeviation(
                metricType = "Sleep",
                currentValue = 7.5,
                baselineValue = 7.2,
                deviationScore = 0.12,
                status = BaselineStatus.NORMAL,
                description = "Sleep duration is slightly above your personal baseline."
            ),

            HealthDeviation(
                metricType = "Steps",
                currentValue = 8432.0,
                baselineValue = 7500.0,
                deviationScore = 0.35,
                status = BaselineStatus.ABOVE_NORMAL,
                description = "Today's activity is above your usual level."
            ),

            HealthDeviation(
                metricType = "Weight",
                currentValue = 70.0,
                baselineValue = 69.5,
                deviationScore = 0.08,
                status = BaselineStatus.NORMAL,
                description = "Weight is close to your personal baseline."
            )
        )

        // ========================================================
        // RECENT HEALTH EVENTS
        // ========================================================

        val recentEvents = listOf(

            HealthEvent(
                id = "event-001",
                metricType = "Heart Rate",
                value = 72.0,
                unit = "bpm",
                timestamp = "2026-09-06T09:42:00",
                source = "Development Data",
                quality = "Good"
            ),

            HealthEvent(
                id = "event-002",
                metricType = "Steps",
                value = 8432.0,
                unit = "steps",
                timestamp = "2026-09-06T14:30:00",
                source = "Development Data",
                quality = "Good"
            ),

            HealthEvent(
                id = "event-003",
                metricType = "Sleep",
                value = 7.5,
                unit = "hours",
                timestamp = "2026-09-06T07:30:00",
                source = "Development Data",
                quality = "Good"
            )
        )

        // ========================================================
        // COMPLETE DIGITAL TWIN
        // ========================================================

        return DigitalTwin(
            profile = profile,
            currentMetrics = currentMetrics,
            baselines = baselines,
            trends = trends,
            deviations = deviations,
            recentEvents = recentEvents,
            overallState = HealthState.STABLE
        )
    }
}