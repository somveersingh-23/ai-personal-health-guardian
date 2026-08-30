package com.healthguardian.sensor.healthconnect

import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.HeartRateVariabilityRmssdRecord
import androidx.health.connect.client.records.OxygenSaturationRecord
import androidx.health.connect.client.records.Record
import androidx.health.connect.client.records.RespiratoryRateRecord
import androidx.health.connect.client.records.RestingHeartRateRecord
import androidx.health.connect.client.records.SkinTemperatureRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.records.metadata.Metadata
import com.healthguardian.sensor.domain.InstantReading
import com.healthguardian.sensor.domain.IntervalReading
import com.healthguardian.sensor.domain.ReadingProvenance
import com.healthguardian.sensor.domain.SensorReading
import com.healthguardian.sensor.domain.SeriesPoint
import com.healthguardian.sensor.domain.SeriesReading
import com.healthguardian.sensor.domain.SessionReading
import com.healthguardian.sensor.domain.SleepStage
import java.nio.charset.StandardCharsets
import java.time.ZoneOffset
import java.util.UUID

object HealthConnectMapper {
    fun map(record: Record, permissionState: String): SensorReading = when (record) {
        is HeartRateRecord -> SeriesReading(
            metric = "heart_rate",
            unit = "bpm",
            provenance = provenance(record),
            permissionState = permissionState,
            startAt = record.startTime,
            endAt = record.endTime,
            startTimezoneOffsetMinutes = minutes(record.startZoneOffset),
            endTimezoneOffsetMinutes = minutes(record.endZoneOffset),
            samples = record.samples.map { SeriesPoint(it.time, it.beatsPerMinute.toDouble()) },
        )
        is RestingHeartRateRecord -> InstantReading(
            metric = "resting_heart_rate",
            unit = "bpm",
            provenance = provenance(record),
            permissionState = permissionState,
            observedAt = record.time,
            timezoneOffsetMinutes = minutes(record.zoneOffset),
            value = record.beatsPerMinute.toDouble(),
        )
        is HeartRateVariabilityRmssdRecord -> InstantReading(
            metric = "hrv_rmssd",
            unit = "ms",
            provenance = provenance(record),
            permissionState = permissionState,
            observedAt = record.time,
            timezoneOffsetMinutes = minutes(record.zoneOffset),
            value = record.heartRateVariabilityMillis,
        )
        is OxygenSaturationRecord -> InstantReading(
            metric = "spo2",
            unit = "%",
            provenance = provenance(record),
            permissionState = permissionState,
            observedAt = record.time,
            timezoneOffsetMinutes = minutes(record.zoneOffset),
            value = record.percentage.value,
        )
        is RespiratoryRateRecord -> InstantReading(
            metric = "respiration_rate",
            unit = "breaths/min",
            provenance = provenance(record),
            permissionState = permissionState,
            observedAt = record.time,
            timezoneOffsetMinutes = minutes(record.zoneOffset),
            value = record.rate,
        )
        is StepsRecord -> IntervalReading(
            metric = "steps",
            unit = "count",
            provenance = provenance(record),
            permissionState = permissionState,
            startAt = record.startTime,
            endAt = record.endTime,
            startTimezoneOffsetMinutes = minutes(record.startZoneOffset),
            endTimezoneOffsetMinutes = minutes(record.endZoneOffset),
            value = record.count.toDouble(),
        )
        is ActiveCaloriesBurnedRecord -> IntervalReading(
            metric = "active_calories",
            unit = "kcal",
            provenance = provenance(record),
            permissionState = permissionState,
            startAt = record.startTime,
            endAt = record.endTime,
            startTimezoneOffsetMinutes = minutes(record.startZoneOffset),
            endTimezoneOffsetMinutes = minutes(record.endZoneOffset),
            value = record.energy.inKilocalories,
        )
        is SkinTemperatureRecord -> SeriesReading(
            metric = "skin_temperature",
            unit = "degC_delta",
            provenance = provenance(record),
            permissionState = permissionState,
            startAt = record.startTime,
            endAt = record.endTime,
            startTimezoneOffsetMinutes = minutes(record.startZoneOffset),
            endTimezoneOffsetMinutes = minutes(record.endZoneOffset),
            samples = record.deltas.map { SeriesPoint(it.time, it.delta.inCelsius) },
        )
        is SleepSessionRecord -> SessionReading(
            provenance = provenance(record),
            permissionState = permissionState,
            startAt = record.startTime,
            endAt = record.endTime,
            startTimezoneOffsetMinutes = minutes(record.startZoneOffset),
            endTimezoneOffsetMinutes = minutes(record.endZoneOffset),
            stages = record.stages.map {
                SleepStage(it.startTime, it.endTime, sleepStageName(it.stage))
            },
        )
        else -> error("Unsupported Health Connect record: ${record::class.qualifiedName}")
    }

    private fun provenance(record: Record): ReadingProvenance {
        val metadata = record.metadata
        val device = metadata.device
        val deviceProfileId = device?.let {
            val identity = listOf(
                metadata.dataOrigin.packageName,
                it.manufacturer ?: "unknown-manufacturer",
                it.model ?: "unknown-model",
                it.type.toString(),
            ).joinToString(":")
            UUID.nameUUIDFromBytes(identity.toByteArray(StandardCharsets.UTF_8)).toString()
        }
        return ReadingProvenance(
            dataOriginPackage = metadata.dataOrigin.packageName,
            sourceRecordType = record::class.simpleName ?: "UnknownRecord",
            sourceRecordId = metadata.id,
            sourceLastModifiedAt = metadata.lastModifiedTime,
            recordingMethod = recordingMethod(metadata.recordingMethod),
            clientRecordId = metadata.clientRecordId,
            clientRecordVersion = metadata.clientRecordVersion,
            deviceId = deviceProfileId,
            deviceManufacturer = device?.manufacturer,
            deviceModel = device?.model,
            deviceType = device?.type?.let(::deviceTypeName),
            deviceTypeCode = device?.type,
        )
    }

    private fun recordingMethod(value: Int): String = when (value) {
        Metadata.RECORDING_METHOD_ACTIVELY_RECORDED -> "actively_recorded"
        Metadata.RECORDING_METHOD_AUTOMATICALLY_RECORDED -> "automatically_recorded"
        Metadata.RECORDING_METHOD_MANUAL_ENTRY -> "manual_entry"
        else -> "unknown"
    }

    private fun minutes(offset: ZoneOffset?): Int? = offset?.totalSeconds?.div(60)

    private fun deviceTypeName(value: Int): String = when (value) {
        1 -> "watch"
        2 -> "phone"
        3 -> "scale"
        4 -> "ring"
        5 -> "head_mounted"
        6 -> "fitness_band"
        7 -> "chest_strap"
        8 -> "smart_display"
        else -> "unknown"
    }

    // Health Connect defines these integer stage values on SleepSessionRecord.
    private fun sleepStageName(value: Int): String = when (value) {
        1 -> "awake"
        2 -> "sleeping"
        3 -> "out_of_bed"
        4 -> "light"
        5 -> "deep"
        6 -> "rem"
        7 -> "awake_in_bed"
        else -> "unknown"
    }
}
