package com.healthguardian.app.feature.sensors.sync

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import com.healthguardian.app.BuildConfig
import com.healthguardian.app.feature.sensors.healthconnect.HealthConnectAccess
import com.healthguardian.app.feature.sensors.healthconnect.SyncTokenStore
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.healthguardian.app.feature.sensors.network.SensorBackendException
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.CancellationException

internal fun retrySensorSync(error: Exception): Boolean = when (error) {
    is CancellationException -> throw error
    is SecurityException, is SensorConfigurationException, is IllegalArgumentException -> false
    is SensorBackendException -> error.statusCode in 500..599 || error.statusCode == 429
    else -> true // Includes Health Connect quota/IPC IllegalStateException.
}

class SensorSyncWorker(
    appContext: Context,
    workerParameters: WorkerParameters,
) : CoroutineWorker(appContext, workerParameters) {
    override suspend fun doWork(): Result {
        return try {
            if (!Member2Runtime.restoreLocalProfileBackend(applicationContext, BuildConfig.API_BASE_URL)) {
                return Result.failure()
            }
            val permission = HealthConnectAccess.permissionSnapshot(HealthConnectClient.getOrCreate(applicationContext))
            if (!permission.backgroundReadAvailable ||
                !BackgroundSyncPolicy.shouldSchedule(SyncTokenStore(applicationContext).isPaused(), permission.granted)) {
                return Result.failure()
            }
            val result = Member2Runtime.sync(applicationContext)
            if (result.failedTypes.isEmpty()) Result.success() else Result.failure()
        } catch (error: Exception) {
            if (retrySensorSync(error)) Result.retry() else Result.failure()
        }
    }
}

object SensorSyncScheduler {
    private const val UNIQUE_WORK = "member2_health_connect_sync"

    suspend fun enable(context: Context) {
        require(Member2Runtime.restoreLocalProfileBackend(context, BuildConfig.API_BASE_URL)) {
            "configure the local profile before scheduling background sync"
        }
        val client = HealthConnectClient.getOrCreate(context)
        val snapshot = HealthConnectAccess.permissionSnapshot(client)
        val granted = snapshot.granted
        val paused = SyncTokenStore(context).isPaused()
        require(snapshot.backgroundReadAvailable && BackgroundSyncPolicy.shouldSchedule(paused, granted)) {
            "sensor sync must be active and background Health Connect permission granted"
        }
        val request = PeriodicWorkRequestBuilder<SensorSyncWorker>(1, TimeUnit.HOURS)
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .setRequiresBatteryNotLow(true)
                    .build(),
            )
            .setBackoffCriteria(
                androidx.work.BackoffPolicy.EXPONENTIAL,
                30,
                TimeUnit.SECONDS,
            )
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            UNIQUE_WORK,
            ExistingPeriodicWorkPolicy.KEEP,
            request,
        )
    }

    fun disable(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(UNIQUE_WORK)
    }
}
