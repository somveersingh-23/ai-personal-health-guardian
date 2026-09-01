package com.healthguardian.sensor.ble

import java.security.MessageDigest
import java.time.Instant
import java.util.UUID

/**
 * Evidence-gated BLE acquisition boundary for future physical-device studies.
 *
 * This is deliberately not a generic "heart-rate BLE" implementation: a BLE UUID alone does
 * not establish signal semantics, calibration or medical validity. A vendor/device profile and
 * a redacted evidence reference are required before a characteristic notification is accepted.
 */
enum class BleSignalKind {
    RAW_PPG,
    ACCELERATION_XYZ,
    DEVICE_REPORTED_HEART_RATE,
    DEVICE_REPORTED_SPO2,
}

enum class BleSessionState {
    IDLE,
    BLOCKED,
    READY_TO_CONNECT,
    CONNECTED,
    DISCONNECTED,
}

data class BleCharacteristicBinding(
    val signal: BleSignalKind,
    val serviceUuid: String,
    val characteristicUuid: String,
    val expectedSamplingRateHz: Double? = null,
    val decoderId: String,
) {
    init {
        UUID.fromString(serviceUuid)
        UUID.fromString(characteristicUuid)
        require(expectedSamplingRateHz == null || expectedSamplingRateHz > 0.0) {
            "expected sampling rate must be positive"
        }
        require(decoderId.isNotBlank()) { "decoderId is required" }
    }
}

data class BleDeviceEvidenceProfile(
    /** Opaque local study alias; never a Bluetooth MAC address, serial number or account ID. */
    val deviceAlias: String,
    val manufacturer: String,
    val model: String,
    val firmwareVersion: String,
    /** Redacted protocol/log location recorded outside this repository. */
    val evidenceReference: String,
    val validationProtocolVersion: String,
    val bindings: List<BleCharacteristicBinding>,
    val supportStatus: String = "research_only",
) {
    init {
        require(deviceAlias.matches(Regex("[A-Za-z0-9._-]{3,64}"))) {
            "deviceAlias must be an opaque safe identifier"
        }
        require(!MAC_ADDRESS.matches(deviceAlias)) { "Bluetooth MAC addresses must not be persisted" }
        require(manufacturer.isNotBlank() && model.isNotBlank() && firmwareVersion.isNotBlank())
        require(evidenceReference.isNotBlank() && validationProtocolVersion.isNotBlank())
        require(bindings.isNotEmpty()) { "at least one characteristic binding is required" }
        require(supportStatus == "research_only") {
            "BLE profiles cannot self-certify supported or clinical status"
        }
        require(bindings.map { it.characteristicUuid.lowercase() }.distinct().size == bindings.size) {
            "a characteristic can only have one declared signal meaning"
        }
    }

    fun stableResearchDeviceId(): String = sha256(
        listOf(deviceAlias, manufacturer, model, firmwareVersion).joinToString("\u001f"),
    ).take(32)

    private companion object {
        val MAC_ADDRESS = Regex("(?i)([0-9a-f]{2}:){5}[0-9a-f]{2}")

        fun sha256(value: String): String = MessageDigest.getInstance("SHA-256")
            .digest(value.toByteArray())
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }
    }
}

data class BleCaptureConsent(
    val active: Boolean,
    val purposeVersion: String,
) {
    init {
        require(purposeVersion.isNotBlank()) { "purposeVersion is required" }
    }
}

data class BleSessionDecision(
    val allowed: Boolean,
    val reasons: List<String>,
)

data class BleResearchFrame(
    val deviceResearchId: String,
    val signal: BleSignalKind,
    val characteristicUuid: String,
    val observedAt: Instant,
    val payload: ByteArray,
    val processingScope: String = "local_research_capture_only",
)

/** Android 12+ and Android 11-and-below permission policy, kept testable without a device. */
object BlePermissionPolicy {
    const val BLUETOOTH_SCAN = "android.permission.BLUETOOTH_SCAN"
    const val BLUETOOTH_CONNECT = "android.permission.BLUETOOTH_CONNECT"
    const val ACCESS_FINE_LOCATION = "android.permission.ACCESS_FINE_LOCATION"

    fun requiredRuntimePermissions(apiLevel: Int): Set<String> =
        if (apiLevel >= 31) setOf(BLUETOOTH_SCAN, BLUETOOTH_CONNECT) else setOf(ACCESS_FINE_LOCATION)
}

/**
 * State machine around a future Android GATT transport. It never decodes vendor bytes into
 * health metrics and never uploads raw frames; a reviewed, device-specific decoder owns that
 * later step after physical evidence exists.
 */
class BleResearchConnector {
    var state: BleSessionState = BleSessionState.IDLE
        private set
    private var profile: BleDeviceEvidenceProfile? = null

    @Synchronized
    fun prepare(
        profile: BleDeviceEvidenceProfile,
        apiLevel: Int,
        grantedPermissions: Set<String>,
        consent: BleCaptureConsent,
    ): BleSessionDecision {
        val missingPermissions = BlePermissionPolicy.requiredRuntimePermissions(apiLevel) - grantedPermissions
        val reasons = buildList {
            if (!consent.active) add("research_capture_consent_inactive")
            if (missingPermissions.isNotEmpty()) add("ble_permissions_missing")
        }
        if (reasons.isNotEmpty()) {
            state = BleSessionState.BLOCKED
            this.profile = null
            return BleSessionDecision(false, reasons)
        }
        this.profile = profile
        state = BleSessionState.READY_TO_CONNECT
        return BleSessionDecision(true, emptyList())
    }

    @Synchronized
    fun markConnected() {
        check(state == BleSessionState.READY_TO_CONNECT) { "BLE session was not prepared" }
        state = BleSessionState.CONNECTED
    }

    @Synchronized
    fun acceptNotification(
        characteristicUuid: String,
        payload: ByteArray,
        observedAt: Instant,
    ): BleResearchFrame {
        check(state == BleSessionState.CONNECTED) { "BLE session is not connected" }
        require(payload.isNotEmpty()) { "empty BLE notification payload" }
        val activeProfile = checkNotNull(profile) { "BLE profile is missing" }
        val binding = activeProfile.bindings.singleOrNull {
            it.characteristicUuid.equals(characteristicUuid, ignoreCase = true)
        } ?: throw IllegalArgumentException("undeclared BLE characteristic notification")
        return BleResearchFrame(
            deviceResearchId = activeProfile.stableResearchDeviceId(),
            signal = binding.signal,
            characteristicUuid = binding.characteristicUuid,
            observedAt = observedAt,
            payload = payload.copyOf(),
        )
    }

    @Synchronized
    fun declaredBindings(): List<BleCharacteristicBinding> =
        checkNotNull(profile) { "BLE profile is missing" }.bindings.toList()

    @Synchronized
    fun disconnect() {
        profile = null
        state = BleSessionState.DISCONNECTED
    }
}
