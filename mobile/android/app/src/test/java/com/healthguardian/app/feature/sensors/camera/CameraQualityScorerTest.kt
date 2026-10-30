package com.healthguardian.app.feature.sensors.camera

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CameraQualityScorerTest {
    @Test
    fun acceptsWellExposedDetailedStableFrame() {
        val values = DoubleArray(25) { index -> if ((index + index / 5) % 2 == 0) 0.2 else 0.8 }

        val result = CameraQualityScorer.evaluate(values, width = 5, height = 5, previous = values)

        assertTrue(result.acceptable)
        assertTrue(result.reasons.isEmpty())
    }

    @Test
    fun rejectsDarkClippedFrame() {
        val values = DoubleArray(25) { 0.0 }

        val result = CameraQualityScorer.evaluate(values, width = 5, height = 5)

        assertFalse(result.acceptable)
        assertTrue("lighting reason expected", result.reasons.any { "lighting" in it })
        assertTrue("exposure reason expected", result.reasons.any { "exposure" in it })
    }
}
