package com.healthguardian.sensor.healthconnect

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.HealthConnectFeatures
import androidx.health.connect.client.permission.HealthPermission
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
import kotlin.reflect.KClass

enum class HealthConnectAvailability {
    AVAILABLE,
    UPDATE_REQUIRED,
    UNAVAILABLE,
}

data class PermissionSnapshot(
    val required: Set<String>,
    val granted: Set<String>,
    val backgroundReadAvailable: Boolean,
    val historyReadAvailable: Boolean,
) {
    val missingRequired: Set<String> = required - granted
    val allRequiredGranted: Boolean = missingRequired.isEmpty()
}

object HealthConnectAccess {
    const val PROVIDER_PACKAGE_NAME = "com.google.android.apps.healthdata"

    val baseRecordTypes: Set<KClass<out Record>> = setOf(
        HeartRateRecord::class,
        RestingHeartRateRecord::class,
        HeartRateVariabilityRmssdRecord::class,
        OxygenSaturationRecord::class,
        RespiratoryRateRecord::class,
        StepsRecord::class,
        SleepSessionRecord::class,
        ActiveCaloriesBurnedRecord::class,
    )

    fun availability(context: Context): HealthConnectAvailability = when (
        HealthConnectClient.getSdkStatus(context, PROVIDER_PACKAGE_NAME)
    ) {
        HealthConnectClient.SDK_AVAILABLE -> HealthConnectAvailability.AVAILABLE
        HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> {
            HealthConnectAvailability.UPDATE_REQUIRED
        }
        else -> HealthConnectAvailability.UNAVAILABLE
    }

    fun supportedRecordTypes(client: HealthConnectClient): Set<KClass<out Record>> = buildSet {
        addAll(baseRecordTypes)
        if (
            client.features.getFeatureStatus(HealthConnectFeatures.FEATURE_SKIN_TEMPERATURE) ==
            HealthConnectFeatures.FEATURE_STATUS_AVAILABLE
        ) {
            add(SkinTemperatureRecord::class)
        }
    }

    fun requiredPermissions(client: HealthConnectClient): Set<String> =
        supportedRecordTypes(client).mapTo(mutableSetOf()) { HealthPermission.getReadPermission(it) }

    suspend fun permissionSnapshot(client: HealthConnectClient): PermissionSnapshot {
        val granted = client.permissionController.getGrantedPermissions()
        return PermissionSnapshot(
            required = requiredPermissions(client),
            granted = granted,
            backgroundReadAvailable = featureAvailable(
                client,
                HealthConnectFeatures.FEATURE_READ_HEALTH_DATA_IN_BACKGROUND,
            ),
            historyReadAvailable = featureAvailable(
                client,
                HealthConnectFeatures.FEATURE_READ_HEALTH_DATA_HISTORY,
            ),
        )
    }

    fun optionalBackgroundPermission(): String =
        HealthPermission.PERMISSION_READ_HEALTH_DATA_IN_BACKGROUND

    fun optionalHistoryPermission(): String = HealthPermission.PERMISSION_READ_HEALTH_DATA_HISTORY

    private fun featureAvailable(client: HealthConnectClient, feature: Int): Boolean =
        client.features.getFeatureStatus(feature) == HealthConnectFeatures.FEATURE_STATUS_AVAILABLE
}
