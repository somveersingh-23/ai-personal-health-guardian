package com.healthguardian.sensor.sync

import com.healthguardian.sensor.healthconnect.HealthConnectAccess
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BackgroundSyncPolicyTest {
    @Test
    fun schedulesOnlyWhenUnpausedAndBackgroundPermissionIsGranted() {
        val background = setOf(HealthConnectAccess.optionalBackgroundPermission())

        assertTrue(BackgroundSyncPolicy.shouldSchedule(paused = false, background))
        assertFalse(BackgroundSyncPolicy.shouldSchedule(paused = true, background))
        assertFalse(BackgroundSyncPolicy.shouldSchedule(paused = false, emptySet()))
    }
}
