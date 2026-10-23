package com.healthguardian.app

import com.healthguardian.app.data.mapper.toDomain
import com.healthguardian.app.data.remote.dto.Member1BaselineDTO
import com.healthguardian.app.data.remote.dto.Member1DigitalTwinResponse
import com.healthguardian.app.data.remote.dto.Member1MetricDTO
import com.healthguardian.app.domain.model.BaselineStatus
import com.healthguardian.app.domain.model.HealthState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Member1DigitalTwinMapperTest {

    @Test
    fun mapsApiMetricsAndBaselineToDomainModels() {
        val response = Member1DigitalTwinResponse(
            user_id = 1,
            state = "stable",
            current_metrics = listOf(
                Member1MetricDTO(
                    type = "heart_rate",
                    value = 72.0,
                    unit = "bpm",
                    timestamp = "2026-10-23T08:00:00Z"
                )
            ),
            baselines = listOf(
                Member1BaselineDTO(
                    event_type = "heart_rate",
                    mean = 70.0,
                    std = 4.0,
                    lower_bound = 62.0,
                    upper_bound = 78.0
                )
            )
        )

        val twin = response.toDomain()

        assertEquals(HealthState.STABLE, twin.overallState)
        assertEquals(1, twin.currentMetrics.size)
        assertEquals("Heart Rate", twin.currentMetrics.first().type)
        assertEquals(BaselineStatus.NORMAL, twin.baselines.first().status)
        assertTrue(twin.recentEvents.isEmpty())
    }

    @Test
    fun mapsUnknownStateSafely() {
        val response = Member1DigitalTwinResponse(
            user_id = 2,
            state = "unrecognized",
            current_metrics = emptyList()
        )

        assertEquals(HealthState.UNKNOWN, response.toDomain().overallState)
    }
}
