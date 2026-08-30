package com.healthguardian.sensor.sync

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import com.healthguardian.sensor.healthconnect.HealthConnectAvailability
import com.healthguardian.sensor.healthconnect.HealthConnectAccess
import com.healthguardian.sensor.healthconnect.HealthConnectSyncEngine
import com.healthguardian.sensor.healthconnect.SyncSummary
import com.healthguardian.sensor.healthconnect.SyncTokenStore
import com.healthguardian.sensor.network.AccessTokenProvider
import com.healthguardian.sensor.network.HttpSensorBackend
import com.healthguardian.sensor.network.ObservationGovernanceProvider
import com.healthguardian.sensor.network.SensorBackend

/**
 * Integration seam for Member 3 authentication/application startup.
 * Configure with an HTTPS backend and a token provider; tokens are never accepted as Worker input data.
 */
object Member2Runtime {
    @Volatile
    private var backend: SensorBackend? = null

    fun configure(sensorBackend: SensorBackend) {
        backend = sensorBackend
    }

    /** Member 3/shared app startup calls this after its authenticated token source is ready. */
    fun configureAuthenticatedBackend(
        baseUrl: String,
        tokenProvider: AccessTokenProvider,
    ) {
        configure(HttpSensorBackend(baseUrl, tokenProvider))
    }

    /**
     * Production v3 configuration. The provider must return the active server-issued
     * consent receipt and purpose version for each upload attempt.
     */
    fun configureGovernedBackend(
        baseUrl: String,
        tokenProvider: AccessTokenProvider,
        governanceProvider: ObservationGovernanceProvider,
    ) {
        configure(HttpSensorBackend(baseUrl, tokenProvider, governanceProvider))
    }

    fun isConfigured(): Boolean = backend != null

    fun clear() {
        backend = null
    }

    suspend fun sync(context: Context): SyncSummary {
        check(HealthConnectAccess.availability(context) == HealthConnectAvailability.AVAILABLE) {
            "Health Connect is not available"
        }
        val configuredBackend = checkNotNull(backend) {
            "Member 3 must configure authenticated SensorBackend before sync"
        }
        val client = HealthConnectClient.getOrCreate(context)
        return HealthConnectSyncEngine(
            context = context,
            client = client,
            tokenStore = SyncTokenStore(context),
            backend = configuredBackend,
        ).syncAll()
    }
}
