package com.healthguardian.app.feature.sensors.sync

import com.healthguardian.app.feature.sensors.healthconnect.HealthConnectAccess

object BackgroundSyncPolicy {
    fun shouldSchedule(paused: Boolean, grantedPermissions: Set<String>): Boolean =
        !paused && HealthConnectAccess.optionalBackgroundPermission() in grantedPermissions
}
