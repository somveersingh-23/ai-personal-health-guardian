package com.healthguardian.sensor.healthconnect

import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.HeartRateVariabilityRmssdRecord
import androidx.health.connect.client.records.OxygenSaturationRecord
import androidx.health.connect.client.records.RespiratoryRateRecord
import androidx.health.connect.client.records.RestingHeartRateRecord
import androidx.health.connect.client.records.SkinTemperatureRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.records.metadata.Device
import androidx.health.connect.client.units.Energy
import androidx.health.connect.client.units.Percentage
import androidx.health.connect.client.units.TemperatureDelta
import com.healthguardian.sensor.domain.InstantReading
import com.healthguardian.sensor.domain.IntervalReading
import com.healthguardian.sensor.domain.ObservationGovernance
import com.healthguardian.sensor.domain.SeriesReading
import com.healthguardian.sensor.domain.SessionReading
import java.time.Instant
import java.time.ZoneOffset
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class HealthConnectMapperTest {
    private val device = Device(
        manufacturer = "Samsung",
        model = "Galaxy Watch 6",
        type = Device.TYPE_WATCH,
    )
    private val testMetadata = createTestMetadata(
        id = "test_rec_001",
        dataOriginPackage = "com.samsung.shealth",
        lastModifiedTime = Instant.parse("2026-08-29T10:00:00Z"),
        device = device,
    )

    @Test
    fun mapsRestingHeartRateRecordToInstantReading() {
        val record = RestingHeartRateRecord(
            time = Instant.parse("2026-08-29T07:30:00Z"),
            zoneOffset = ZoneOffset.ofHoursMinutes(5, 30),
            beatsPerMinute = 62,
            metadata = testMetadata,
        )

        val reading = HealthConnectMapper.map(record, "granted_foreground") as InstantReading

        assertEquals("resting_heart_rate", reading.metric)
        assertEquals("bpm", reading.unit)
        assertEquals(62.0, reading.value, 0.001)
        assertEquals(330, reading.timezoneOffsetMinutes)
        assertEquals("granted_foreground", reading.permissionState)
        assertEquals("com.samsung.shealth", reading.provenance.dataOriginPackage)
        assertEquals("Samsung", reading.provenance.deviceManufacturer)
        assertEquals("Galaxy Watch 6", reading.provenance.deviceModel)
        assertEquals("watch", reading.provenance.deviceType)
        assertNotNull(reading.provenance.deviceId)

        val json = reading.toJson()
        assertEquals("2.0.0", json.getString("schema_version"))
        assertEquals("instant", json.getString("temporal_type"))
        assertNotNull(json.getString("event_id"))

        val governedJson = reading.toJson(
            ObservationGovernance(
                consentReceiptId = "123e4567-e89b-12d3-a456-426614174000",
                purposeVersion = "wellness-v1",
            ),
        )
        assertEquals("3.0.0", governedJson.getString("schema_version"))
        assertEquals(
            "123e4567-e89b-12d3-a456-426614174000",
            governedJson.getString("consent_receipt_id"),
        )
        assertEquals("wellness-v1", governedJson.getString("purpose_version"))
        assertEquals("health-connect-android-v3", governedJson.getString("mapper_version"))
        assertEquals(
            Device.TYPE_WATCH,
            governedJson.getJSONObject("metadata").getInt("health_connect_device_type_code"),
        )
    }

    @Test
    fun mapsHeartRateVariabilityRecord() {
        val record = HeartRateVariabilityRmssdRecord(
            time = Instant.parse("2026-08-29T07:30:00Z"),
            zoneOffset = ZoneOffset.UTC,
            heartRateVariabilityMillis = 48.5,
            metadata = testMetadata,
        )

        val reading = HealthConnectMapper.map(record, "granted_background") as InstantReading

        assertEquals("hrv_rmssd", reading.metric)
        assertEquals("ms", reading.unit)
        assertEquals(48.5, reading.value, 0.001)
        assertEquals(0, reading.timezoneOffsetMinutes)
        assertEquals("granted_background", reading.permissionState)
    }

    @Test
    fun mapsOxygenSaturationRecord() {
        val record = OxygenSaturationRecord(
            time = Instant.parse("2026-08-29T07:30:00Z"),
            zoneOffset = ZoneOffset.UTC,
            percentage = Percentage(98.0),
            metadata = testMetadata,
        )

        val reading = HealthConnectMapper.map(record, "granted_foreground") as InstantReading

        assertEquals("spo2", reading.metric)
        assertEquals("%", reading.unit)
        assertEquals(98.0, reading.value, 0.001)
    }

    @Test
    fun mapsRespiratoryRateRecord() {
        val record = RespiratoryRateRecord(
            time = Instant.parse("2026-08-29T07:30:00Z"),
            zoneOffset = ZoneOffset.UTC,
            rate = 14.5,
            metadata = testMetadata,
        )

        val reading = HealthConnectMapper.map(record, "granted_foreground") as InstantReading

        assertEquals("respiration_rate", reading.metric)
        assertEquals("breaths/min", reading.unit)
        assertEquals(14.5, reading.value, 0.001)
    }

    @Test
    fun mapsStepsRecordToIntervalReading() {
        val record = StepsRecord(
            startTime = Instant.parse("2026-08-29T08:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T09:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            count = 1500,
            metadata = testMetadata,
        )

        val reading = HealthConnectMapper.map(record, "granted_foreground") as IntervalReading

        assertEquals("steps", reading.metric)
        assertEquals("count", reading.unit)
        assertEquals(1500.0, reading.value, 0.001)

        val json = reading.toJson()
        assertEquals("interval", json.getString("temporal_type"))
        assertEquals(1500.0, json.getDouble("value"), 0.001)
    }

    @Test
    fun mapsActiveCaloriesBurnedRecord() {
        val record = ActiveCaloriesBurnedRecord(
            startTime = Instant.parse("2026-08-29T08:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T09:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            energy = Energy.kilocalories(245.5),
            metadata = testMetadata,
        )

        val reading = HealthConnectMapper.map(record, "granted_foreground") as IntervalReading

        assertEquals("active_calories", reading.metric)
        assertEquals("kcal", reading.unit)
        assertEquals(245.5, reading.value, 0.001)
    }

    @Test
    fun mapsSkinTemperatureRecordWithDeltaUnits() {
        val record = SkinTemperatureRecord(
            startTime = Instant.parse("2026-08-29T02:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T03:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            deltas = listOf(
                SkinTemperatureRecord.Delta(
                    time = Instant.parse("2026-08-29T02:15:00Z"),
                    delta = TemperatureDelta.celsius(0.35),
                ),
            ),
            metadata = testMetadata,
        )

        val reading = HealthConnectMapper.map(record, "granted_foreground") as SeriesReading

        assertEquals("skin_temperature", reading.metric)
        assertEquals("degC_delta", reading.unit)
        assertEquals(1, reading.samples.size)
        assertEquals(0.35, reading.samples[0].value, 0.001)
    }

    @Test
    fun mapsSleepSessionRecordWithStages() {
        val record = SleepSessionRecord(
            startTime = Instant.parse("2026-08-29T00:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T07:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            stages = listOf(
                SleepSessionRecord.Stage(
                    startTime = Instant.parse("2026-08-29T00:00:00Z"),
                    endTime = Instant.parse("2026-08-29T00:30:00Z"),
                    stage = SleepSessionRecord.STAGE_TYPE_LIGHT,
                ),
                SleepSessionRecord.Stage(
                    startTime = Instant.parse("2026-08-29T00:30:00Z"),
                    endTime = Instant.parse("2026-08-29T02:30:00Z"),
                    stage = SleepSessionRecord.STAGE_TYPE_DEEP,
                ),
                SleepSessionRecord.Stage(
                    startTime = Instant.parse("2026-08-29T02:30:00Z"),
                    endTime = Instant.parse("2026-08-29T03:00:00Z"),
                    stage = SleepSessionRecord.STAGE_TYPE_AWAKE,
                ),
            ),
            metadata = testMetadata,
        )

        val reading = HealthConnectMapper.map(record, "granted_foreground") as SessionReading

        assertEquals("sleep_duration", reading.metric)
        assertEquals("min", reading.unit)
        assertEquals(3, reading.stages.size)
        assertEquals("light", reading.stages[0].stage)
        assertEquals("deep", reading.stages[1].stage)
        assertEquals("awake", reading.stages[2].stage)

        val json = reading.toJson()
        assertEquals("session", json.getString("temporal_type"))
        assertEquals(3, json.getJSONArray("stages").length())
    }

    @Test
    fun stableEventIdIsDeterministicAcrossIdenticalProvenance() {
        val record1 = StepsRecord(
            startTime = Instant.parse("2026-08-29T08:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T09:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            count = 1000,
            metadata = testMetadata,
        )
        val record2 = StepsRecord(
            startTime = Instant.parse("2026-08-29T08:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T09:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            count = 2000, // Different count, same metadata ID & provenance
            metadata = testMetadata,
        )

        val reading1 = HealthConnectMapper.map(record1, "granted_foreground")
        val reading2 = HealthConnectMapper.map(record2, "granted_foreground")

        assertEquals(
            reading1.toJson().getString("event_id"),
            reading2.toJson().getString("event_id"),
        )
    }
}
