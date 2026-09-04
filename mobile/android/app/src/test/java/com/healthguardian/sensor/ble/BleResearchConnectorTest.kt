package com.healthguardian.sensor.ble

import java.time.Instant
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BleResearchConnectorTest {
    private fun profile() = BleDeviceEvidenceProfile(
        deviceAlias = "study-device-01",
        manufacturer = "Example",
        model = "PPG research board",
        firmwareVersion = "1.0.0",
        evidenceReference = "private://redacted/device-study-01",
        validationProtocolVersion = "ble-study-v1",
        bindings = listOf(
            BleCharacteristicBinding(
                signal = BleSignalKind.RAW_PPG,
                serviceUuid = "00000000-0000-1000-8000-00805f9b34fb",
                characteristicUuid = "00000001-0000-1000-8000-00805f9b34fb",
                expectedSamplingRateHz = 100.0,
                decoderId = "vendor-a-ppg-v1",
            ),
        ),
    )

    @Test
    fun connector_blocks_capture_without_active_consent() {
        val result = BleResearchConnector().prepare(
            profile(),
            34,
            setOf(BlePermissionPolicy.BLUETOOTH_SCAN, BlePermissionPolicy.BLUETOOTH_CONNECT),
            BleCaptureConsent(active = false, purposeVersion = "v1"),
        )

        assertFalse(result.allowed)
        assertTrue("research_capture_consent_inactive" in result.reasons)
    }

    @Test
    fun connector_accepts_only_declared_characteristics_and_keeps_research_scope() {
        val connector = BleResearchConnector()
        val result = connector.prepare(
            profile(),
            34,
            setOf(BlePermissionPolicy.BLUETOOTH_SCAN, BlePermissionPolicy.BLUETOOTH_CONNECT),
            BleCaptureConsent(active = true, purposeVersion = "v1"),
        )
        assertTrue(result.allowed)
        connector.markConnected()

        val frame = connector.acceptNotification(
            "00000001-0000-1000-8000-00805f9b34fb",
            byteArrayOf(1, 2, 3),
            Instant.parse("2026-09-01T00:00:00Z"),
        )

        assertEquals(BleSignalKind.RAW_PPG, frame.signal)
        assertEquals("local_research_capture_only", frame.processingScope)
        assertEquals(BleSessionState.CONNECTED, connector.state)
    }

    @Test(expected = IllegalArgumentException::class)
    fun connector_rejects_undeclared_characteristics() {
        val connector = BleResearchConnector()
        connector.prepare(
            profile(),
            30,
            setOf(BlePermissionPolicy.ACCESS_FINE_LOCATION),
            BleCaptureConsent(active = true, purposeVersion = "v1"),
        )
        connector.markConnected()
        connector.acceptNotification(
            "00000002-0000-1000-8000-00805f9b34fb",
            byteArrayOf(1),
            Instant.now(),
        )
    }
}
