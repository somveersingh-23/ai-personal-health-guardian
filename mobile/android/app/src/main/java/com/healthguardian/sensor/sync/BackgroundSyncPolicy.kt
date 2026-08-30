package com.healthguardian.sensor.sync

import com.healthguardian.sensor.healthconnect.HealthConnectAccess

object BackgroundSyncPolicy {
    fun shouldSchedule(paused: Boolean, grantedPermissions: Set<String>): Boolean =
        !paused && HealthConnectAccess.optionalBackgroundPermission() in grantedPermissions
}
