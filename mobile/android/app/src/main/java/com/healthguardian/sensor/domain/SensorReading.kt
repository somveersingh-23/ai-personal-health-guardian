package com.healthguardian.sensor.domain

import java.nio.charset.StandardCharsets
import java.time.Instant
import java.util.UUID
import org.json.JSONArray
import org.json.JSONObject

data class ReadingProvenance(
    val dataOriginPackage: String,
    val sourceRecordType: String,
    val sourceRecordId: String,
    val sourceLastModifiedAt: Instant,
    val recordingMethod: String,
    val clientRecordId: String? = null,
    val clientRecordVersion: Long? = null,
    val deviceId: String? = null,
    val deviceManufacturer: String? = null,
    val deviceModel: String? = null,
    val deviceType: String? = null,
    val deviceTypeCode: Int? = null,
)

data class ObservationGovernance(
    val consentReceiptId: String,
    val purpose: String = "sensor_intelligence_wellness",
    val purposeVersion: String,
    val retentionClass: String = "normalized_observation",
) {
    init {
        UUID.fromString(consentReceiptId)
        require(purposeVersion.isNotBlank()) { "purpose version is required" }
    }
}

data class SeriesPoint(val observedAt: Instant, val value: Double)

data class SleepStage(val startAt: Instant, val endAt: Instant, val stage: String)

sealed interface SensorReading {
    val metric: String
    val unit: String
    val provenance: ReadingProvenance
    val permissionState: String

    fun toJson(governance: ObservationGovernance? = null): JSONObject

    fun commonJson(temporalType: String, governance: ObservationGovernance?): JSONObject = JSONObject().apply {
        put("schema_version", if (governance == null) "2.0.0" else "3.0.0")
        put("event_id", stableEventId(provenance))
        put("temporal_type", temporalType)
        put("metric", metric)
        put("unit", unit)
        put("source", "health_connect")
        put("data_origin_package", provenance.dataOriginPackage)
        put("source_record_type", provenance.sourceRecordType)
        put("source_record_id", provenance.sourceRecordId)
        put("source_last_modified_at", provenance.sourceLastModifiedAt.toString())
        put("recording_method", provenance.recordingMethod)
        put("permission_state", permissionState)
        put(
            "metadata",
            JSONObject().apply {
                if (provenance.deviceTypeCode != null) {
                    put("health_connect_device_type_code", provenance.deviceTypeCode)
                }
            },
        )
        putOptional("client_record_id", provenance.clientRecordId)
        putOptional("client_record_version", provenance.clientRecordVersion)
        putOptional("device_id", provenance.deviceId)
        putOptional("device_manufacturer", provenance.deviceManufacturer)
        putOptional("device_model", provenance.deviceModel)
        putOptional("device_type", provenance.deviceType)
        if (governance != null) {
            put("consent_receipt_id", governance.consentReceiptId)
            put("processing_purpose", governance.purpose)
            put("purpose_version", governance.purposeVersion)
            put("retention_class", governance.retentionClass)
            put("mapper_version", "health-connect-android-v3")
            put("wear_state", "unknown")
            put("motion_state", "unknown")
        }
    }

    companion object {
        private fun stableEventId(provenance: ReadingProvenance): String {
            val identity = listOf(
                provenance.dataOriginPackage,
                provenance.sourceRecordType,
                provenance.sourceRecordId,
            ).joinToString(":")
            return UUID.nameUUIDFromBytes(identity.toByteArray(StandardCharsets.UTF_8)).toString()
        }

        private fun JSONObject.putOptional(name: String, value: Any?) {
            if (value != null) put(name, value)
        }
    }
}

data class InstantReading(
    override val metric: String,
    override val unit: String,
    override val provenance: ReadingProvenance,
    override val permissionState: String,
    val observedAt: Instant,
    val timezoneOffsetMinutes: Int?,
    val value: Double,
) : SensorReading {
    override fun toJson(governance: ObservationGovernance?): JSONObject =
        commonJson("instant", governance).apply {
        put("observed_at", observedAt.toString())
        if (timezoneOffsetMinutes != null) put("timezone_offset_minutes", timezoneOffsetMinutes)
        put("value", value)
    }
}

data class IntervalReading(
    override val metric: String,
    override val unit: String,
    override val provenance: ReadingProvenance,
    override val permissionState: String,
    val startAt: Instant,
    val endAt: Instant,
    val startTimezoneOffsetMinutes: Int?,
    val endTimezoneOffsetMinutes: Int?,
    val value: Double,
) : SensorReading {
    override fun toJson(governance: ObservationGovernance?): JSONObject =
        commonJson("interval", governance).apply {
        put("start_at", startAt.toString())
        put("end_at", endAt.toString())
        if (startTimezoneOffsetMinutes != null) {
            put("start_timezone_offset_minutes", startTimezoneOffsetMinutes)
        }
        if (endTimezoneOffsetMinutes != null) {
            put("end_timezone_offset_minutes", endTimezoneOffsetMinutes)
        }
        put("value", value)
    }
}

data class SeriesReading(
    override val metric: String,
    override val unit: String,
    override val provenance: ReadingProvenance,
    override val permissionState: String,
    val startAt: Instant,
    val endAt: Instant,
    val startTimezoneOffsetMinutes: Int?,
    val endTimezoneOffsetMinutes: Int?,
    val samples: List<SeriesPoint>,
) : SensorReading {
    override fun toJson(governance: ObservationGovernance?): JSONObject =
        commonJson("series", governance).apply {
        put("start_at", startAt.toString())
        put("end_at", endAt.toString())
        if (startTimezoneOffsetMinutes != null) {
            put("start_timezone_offset_minutes", startTimezoneOffsetMinutes)
        }
        if (endTimezoneOffsetMinutes != null) {
            put("end_timezone_offset_minutes", endTimezoneOffsetMinutes)
        }
        put(
            "samples",
            JSONArray(
                samples.map {
                    JSONObject().put("observed_at", it.observedAt.toString()).put("value", it.value)
                },
            ),
        )
    }
}

data class SessionReading(
    override val metric: String = "sleep_duration",
    override val unit: String = "min",
    override val provenance: ReadingProvenance,
    override val permissionState: String,
    val startAt: Instant,
    val endAt: Instant,
    val startTimezoneOffsetMinutes: Int?,
    val endTimezoneOffsetMinutes: Int?,
    val stages: List<SleepStage>,
) : SensorReading {
    override fun toJson(governance: ObservationGovernance?): JSONObject =
        commonJson("session", governance).apply {
        put("start_at", startAt.toString())
        put("end_at", endAt.toString())
        if (startTimezoneOffsetMinutes != null) {
            put("start_timezone_offset_minutes", startTimezoneOffsetMinutes)
        }
        if (endTimezoneOffsetMinutes != null) {
            put("end_timezone_offset_minutes", endTimezoneOffsetMinutes)
        }
        put(
            "stages",
            JSONArray(
                stages.map {
                    JSONObject()
                        .put("start_at", it.startAt.toString())
                        .put("end_at", it.endAt.toString())
                        .put("stage", it.stage)
                },
            ),
        )
    }
}
