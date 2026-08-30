package com.healthguardian.sensor.camera

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CameraQualityScorerTest {
    @Test
    fun flatFrameAbstains() {
        val result = CameraQualityScorer.evaluate(DoubleArray(16 * 16) { 0.5 }, 16, 16)

        assertFalse(result.acceptable)
        assertTrue(result.reasons.any { it.contains("contrast") })
        assertTrue(result.reasons.any { it.contains("refocus") })
    }

    @Test
    fun highMotionFrameAbstains() {
        val first = DoubleArray(16 * 16) { index -> if ((index + index / 16) % 2 == 0) 0.35 else 0.65 }
        val moved = first.map { 1.0 - it }.toDoubleArray()

        val result = CameraQualityScorer.evaluate(moved, 16, 16, first)

        assertFalse(result.acceptable)
        assertTrue(result.reasons.any { it.contains("movement") })
    }

    @Test
    fun exposedSharpStationaryFramePassesCaptureGate() {
        val values = DoubleArray(16 * 16) { index -> if ((index + index / 16) % 2 == 0) 0.35 else 0.65 }

        val result = CameraQualityScorer.evaluate(values, 16, 16, values.copyOf())

        assertTrue(result.acceptable)
    }
}
