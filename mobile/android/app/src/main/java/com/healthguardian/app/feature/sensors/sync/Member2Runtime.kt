package com.healthguardian.app.feature.sensors.sync

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import com.healthguardian.app.feature.sensors.healthconnect.HealthConnectAvailability
import com.healthguardian.app.feature.sensors.healthconnect.HealthConnectAccess
import com.healthguardian.app.feature.sensors.healthconnect.HealthConnectSyncEngine
import com.healthguardian.app.feature.sensors.healthconnect.SyncSummary
import com.healthguardian.app.feature.sensors.healthconnect.SyncTokenStore

/**
 * Process-local runtime backed by a persistent, auth-free profile binding.
 * The binding lets WorkManager rebuild the transport after process death.
 */
object Member2Runtime {
    @Volatile
    private var session: Member2Session? = null

    @Synchronized
    private fun session(context: Context): Member2Session = session ?: Member2Session(
        Member2ConfigurationStore(context.applicationContext),
        SyncTokenStore(context.applicationContext),
    ).also { session = it }

    suspend fun configureLocalProfileBackend(context: Context, baseUrl: String, userId: Int) {
        session(context).configure(LocalProfileConfiguration(userId, baseUrl.trimEnd('/')))
    }

    suspend fun restoreLocalProfileBackend(context: Context, currentBaseUrl: String): Boolean {
        return session(context).restore(currentBaseUrl)
    }

    fun isConfigured(): Boolean = session?.isConfigured() == true

    suspend fun disconnect(context: Context) {
        SensorSyncScheduler.disable(context)
        session(context).disconnect()
    }

    suspend fun sync(context: Context): SyncSummary = session(context).sync { configuredBackend ->
        if (HealthConnectAccess.availability(context) != HealthConnectAvailability.AVAILABLE) {
            throw SensorConfigurationException("Health Connect is not available")
        }
        val client = HealthConnectClient.getOrCreate(context)
        HealthConnectSyncEngine(
            context = context,
            client = client,
            tokenStore = SyncTokenStore(context),
            backend = configuredBackend,
        ).syncAll()
    }
}
