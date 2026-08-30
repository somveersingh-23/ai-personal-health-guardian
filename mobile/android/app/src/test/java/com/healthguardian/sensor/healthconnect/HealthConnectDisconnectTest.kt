package com.healthguardian.sensor.healthconnect

import java.time.Instant
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class HealthConnectDisconnectTest {
    @Test
    fun disconnectClearsLocalStateCancelsWorkAndRevokesPermissions() = runBlocking {
        val client = FakeHealthConnectClient()
        client.fakePermissions.grantedPermissions = setOf("permission.one", "permission.two")
        val store = SyncTokenStore(InMemoryTokenStorage(), TestSyncTokenCipher())
        store.save("StepsRecord", "steps-token", Instant.now())
        var cancellationCalled = false

        val result = HealthConnectDisconnect.execute(client, store) {
            cancellationCalled = true
        }

        assertTrue(result.complete)
        assertTrue(result.localStateCleared)
        assertTrue(result.permissionsRevoked)
        assertTrue(result.backgroundWorkCancelled)
        assertTrue(cancellationCalled)
        assertEquals(1, client.fakePermissions.revokeCallCount)
        assertTrue(client.fakePermissions.grantedPermissions.isEmpty())
        assertTrue(store.isPaused())
        assertNull(store.load("StepsRecord"))
    }

    @Test
    fun platformRevocationFailureStillStopsLocalCollection() = runBlocking {
        val client = FakeHealthConnectClient()
        client.fakePermissions.grantedPermissions = setOf("permission.one")
        client.fakePermissions.revokeFailure = IllegalStateException("service unavailable")
        val store = SyncTokenStore(InMemoryTokenStorage(), TestSyncTokenCipher())
        store.save("StepsRecord", "steps-token", Instant.now())
        var cancellationCalled = false

        val result = HealthConnectDisconnect.execute(client, store) {
            cancellationCalled = true
        }

        assertFalse(result.complete)
        assertTrue(result.localStateCleared)
        assertFalse(result.permissionsRevoked)
        assertTrue(result.backgroundWorkCancelled)
        assertTrue(cancellationCalled)
        assertTrue(store.isPaused())
        assertNull(store.load("StepsRecord"))
    }
}
