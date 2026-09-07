package com.healthguardian.app.feature.sensors.sync

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.assertNotNull
import com.healthguardian.app.feature.sensors.healthconnect.SyncTokenStore
import com.healthguardian.app.feature.sensors.healthconnect.InMemoryTokenStorage
import com.healthguardian.app.feature.sensors.healthconnect.TestSyncTokenCipher
import com.healthguardian.app.feature.sensors.healthconnect.FakeSensorBackend
import com.healthguardian.app.feature.sensors.network.HttpSensorBackend
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.async
import java.time.Instant
import kotlinx.coroutines.CancellationException
import com.healthguardian.app.feature.sensors.network.SensorBackendException

class Member2RuntimeTest {
    @Test
    fun quotaRetriesButCancellationPropagates() {
        assertTrue(retrySensorSync(IllegalStateException("provider quota")))
        assertTrue(retrySensorSync(SensorBackendException(429)))
        assertTrue(retrySensorSync(SensorBackendException(503)))
        assertFalse(retrySensorSync(SensorBackendException(422)))
        assertFalse(retrySensorSync(SensorConfigurationException("paused")))
        val cancelled = CancellationException("stopped")
        try { retrySensorSync(cancelled); error("cancellation swallowed") }
        catch (actual: CancellationException) { assertTrue(actual === cancelled) }
    }
    private fun tokens() = SyncTokenStore(InMemoryTokenStorage(), TestSyncTokenCipher())

    @Test
    fun profileSwitchDrainsOldSyncBeforeClearingItsCursor() = runBlocking {
        val store = Member2ConfigurationStore(InMemoryMember2ConfigurationStorage())
        val tokens = tokens()
        val session = Member2Session(store, tokens) { FakeSensorBackend() }
        session.configure(LocalProfileConfiguration(1, "https://health.example.test"))
        val release = CompletableDeferred<Unit>()
        val sync = async(start = CoroutineStart.UNDISPATCHED) {
            session.sync { release.await(); tokens.save("StepsRecord", "old-profile", Instant.now()) }
        }
        val switch = async(start = CoroutineStart.UNDISPATCHED) {
            session.configure(LocalProfileConfiguration(2, "https://health.example.test"))
        }
        assertFalse(switch.isCompleted)
        release.complete(Unit)
        sync.await()
        switch.await()
        assertEquals(2, store.load()?.userId)
        assertNull(tokens.load("StepsRecord"))
    }

    @Test
    fun disconnectDrainsOldSyncAndLeavesFinalStatePaused() = runBlocking {
        val store = Member2ConfigurationStore(InMemoryMember2ConfigurationStorage())
        val tokens = tokens()
        val session = Member2Session(store, tokens) { FakeSensorBackend() }
        session.configure(LocalProfileConfiguration(1, "https://health.example.test"))
        val release = CompletableDeferred<Unit>()
        val sync = async(start = CoroutineStart.UNDISPATCHED) {
            session.sync { release.await(); tokens.save("StepsRecord", "old-profile", Instant.now()) }
        }
        val disconnect = async(start = CoroutineStart.UNDISPATCHED) { session.disconnect() }
        assertTrue(tokens.isPaused())
        assertFalse(disconnect.isCompleted)
        release.complete(Unit)
        sync.await()
        disconnect.await()
        assertNull(store.load())
        assertNull(tokens.load("StepsRecord"))
        assertTrue(tokens.isPaused())
        assertFalse(session.isConfigured())
    }

    @Test
    fun processRestartRestoresOnlyTheSameExplicitBackend() = runBlocking {
        val store = Member2ConfigurationStore(InMemoryMember2ConfigurationStorage())
        val tokens = tokens()
        Member2Session(store, tokens).configure(LocalProfileConfiguration(7, "https://health.example.test"))
        tokens.save("StepsRecord", "cursor", Instant.now())
        val restored = Member2Session(store, tokens)
        assertFalse(restored.restore("https://different.example.test"))
        assertNotNull(tokens.load("StepsRecord"))
        assertTrue(restored.restore("https://health.example.test/"))
        assertTrue(restored.isConfigured())
        try {
            restored.configure(LocalProfileConfiguration(8, "http://localhost.evil.example"))
            error("unsafe URL accepted")
        } catch (_: IllegalArgumentException) { }
        assertEquals(7, store.load()?.userId)
        assertNotNull(tokens.load("StepsRecord"))
    }

    @Test
    fun validatesExactUrlHostAndOrigin() {
        listOf("https://health.example.test", "http://localhost:8000", "http://127.0.0.1:8000", "http://10.0.2.2:8000").forEach {
            HttpSensorBackend(it, localUserId = 7)
        }
        listOf("http://localhost.evil.example", "http://127.0.0.1@evil.example", "https://user@health.example.test",
            "https://health.example.test?user_id=8", "https://health.example.test#x", "https://health.example.test/api",
            "http://10.0.2.20", "https://health.example.test:70000").forEach {
            try {
                HttpSensorBackend(it, localUserId = 7)
                error("unsafe URL accepted: $it")
            } catch (_: IllegalArgumentException) { }
        }
    }

    @Test
    fun configurationStorePersistsAndClearsLocalProfileBinding() = runBlocking {
        val store = Member2ConfigurationStore(InMemoryMember2ConfigurationStorage())
        val configuration = LocalProfileConfiguration(42, "https://health.example.test/")

        store.save(configuration)
        assertEquals(configuration.copy(baseUrl = "https://health.example.test"), store.load())

        store.clear()
        assertNull(store.load())
    }
}
