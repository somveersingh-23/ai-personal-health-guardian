package com.healthguardian.app.feature.sensors.sync

import com.healthguardian.app.feature.sensors.healthconnect.SyncTokenStore
import com.healthguardian.app.feature.sensors.network.HttpSensorBackend
import com.healthguardian.app.feature.sensors.network.SensorBackend
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

class SensorConfigurationException(message: String) : IllegalStateException(message)

/** A completed binding change or disconnect cannot be followed by an old sync write. */
internal class Member2Session(
    private val configurations: Member2ConfigurationStore,
    private val tokens: SyncTokenStore,
    private val transport: (LocalProfileConfiguration) -> SensorBackend = {
        HttpSensorBackend(it.baseUrl, localUserId = it.userId)
    },
) {
    private val gate = Mutex()
    @Volatile private var backend: SensorBackend? = null

    fun isConfigured(): Boolean = backend != null

    suspend fun configure(configuration: LocalProfileConfiguration) {
        val configured = transport(configuration)
        gate.withLock {
            backend = null
            tokens.setPaused(true)
            if (configurations.load() != configuration) tokens.clearAll()
            configurations.save(configuration)
            tokens.setPaused(false)
            backend = configured
        }
    }

    suspend fun restore(baseUrl: String): Boolean = gate.withLock {
        val saved = configurations.load() ?: return@withLock false
        if (saved.baseUrl != baseUrl.trimEnd('/') || tokens.isPaused()) return@withLock false
        backend = transport(saved)
        true
    }

    suspend fun disconnect() {
        tokens.setPaused(true)
        gate.withLock {
            backend = null
            tokens.setPaused(true)
            configurations.clear()
            tokens.clearAll()
        }
    }

    suspend fun <T> sync(action: suspend (SensorBackend) -> T): T = gate.withLock {
        if (tokens.isPaused()) throw SensorConfigurationException("sensor sync is paused")
        val current = backend ?: throw SensorConfigurationException("configure the local profile before sync")
        action(current)
    }
}
