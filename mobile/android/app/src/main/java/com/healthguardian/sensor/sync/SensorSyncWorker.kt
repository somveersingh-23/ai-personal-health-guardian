package com.healthguardian.sensor.sync

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import com.healthguardian.sensor.healthconnect.HealthConnectAccess
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.healthguardian.sensor.network.SensorBackendException
import java.util.concurrent.TimeUnit

class SensorSyncWorker(
    appContext: Context,
    workerParameters: WorkerParameters,
) : CoroutineWorker(appContext, workerParameters) {
    override suspend fun doWork(): Result = try {
        Member2Runtime.sync(applicationContext)
        Result.success()
    } catch (_: SecurityException) {
        Result.failure()
    } catch (error: SensorBackendException) {
        if (error.statusCode in 500..599 || error.statusCode == 429) Result.retry() else Result.failure()
    } catch (_: IllegalStateException) {
        Result.failure()
    } catch (_: Exception) {
        Result.retry()
    }
}

object SensorSyncScheduler {
    private const val UNIQUE_WORK = "member2_health_connect_sync"

    suspend fun enable(context: Context) {
        val client = HealthConnectClient.getOrCreate(context)
        val granted = client.permissionController.getGrantedPermissions()
        require(HealthConnectAccess.optionalBackgroundPermission() in granted) {
            "background Health Connect permission must be granted before scheduling"
        }
        val request = PeriodicWorkRequestBuilder<SensorSyncWorker>(1, TimeUnit.HOURS)
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .setRequiresBatteryNotLow(true)
                    .build(),
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
