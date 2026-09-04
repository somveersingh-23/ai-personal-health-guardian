package com.healthguardian.sensor.healthconnect

import androidx.health.connect.client.HealthConnectClient
import kotlinx.coroutines.CancellationException

data class HealthConnectDisconnectResult(
    val localStateCleared: Boolean,
    val permissionsRevoked: Boolean,
    val backgroundWorkCancelled: Boolean,
) {
    val complete: Boolean = localStateCleared && permissionsRevoked && backgroundWorkCancelled
}

object HealthConnectDisconnect {
    /**
     * Stops collection locally before revoking platform permissions. Every cleanup step is attempted,
     * so an unavailable Health Connect service cannot leave background work running.
     */
    suspend fun execute(
        client: HealthConnectClient,
        tokenStore: SyncTokenStore,
        cancelBackgroundWork: () -> Unit,
    ): HealthConnectDisconnectResult {
        val paused = attemptSuspend { tokenStore.setPaused(true) }
        val workCancelled = attemptImmediate(cancelBackgroundWork)
        val tokensCleared = attemptSuspend { tokenStore.clearAll() }
        val permissionsRevoked = attemptSuspend {
            client.permissionController.revokeAllPermissions()
        }
        return HealthConnectDisconnectResult(
            localStateCleared = paused && tokensCleared,
            permissionsRevoked = permissionsRevoked,
            backgroundWorkCancelled = workCancelled,
        )
    }

    private suspend fun attemptSuspend(operation: suspend () -> Unit): Boolean = try {
        operation()
        true
    } catch (cancelled: CancellationException) {
        throw cancelled
    } catch (_: Exception) {
        false
    }

    private fun attemptImmediate(operation: () -> Unit): Boolean = try {
        operation()
        true
    } catch (_: Exception) {
        false
    }
}
