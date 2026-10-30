package com.healthguardian.app.feature.sensors.presentation

import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import com.healthguardian.app.BuildConfig
import com.healthguardian.app.feature.sensors.camera.CameraQualityActivity
import com.healthguardian.app.feature.sensors.healthconnect.HealthConnectAccess
import com.healthguardian.app.feature.sensors.healthconnect.HealthConnectAvailability
import com.healthguardian.app.feature.sensors.healthconnect.HealthConnectDisconnect
import com.healthguardian.app.feature.sensors.healthconnect.SyncTokenStore
import com.healthguardian.app.feature.sensors.sync.Member2Runtime
import com.healthguardian.app.feature.sensors.sync.SensorSyncScheduler
import kotlinx.coroutines.launch
import kotlinx.coroutines.CancellationException
import com.healthguardian.app.feature.sensors.sync.Member2ConfigurationStore

/**
 * M2-owned Health Connect control surface. The profile identifier is entered
 * once for the current local user and then persisted for restart-safe sync.
 */
@Composable
fun HealthConnectScreen(onNavigateBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val availability = remember { HealthConnectAccess.availability(context) }
    var profileId by rememberSaveable { mutableStateOf("") }
    var status by rememberSaveable { mutableStateOf("Check permissions before connecting.") }
    var grantedPermissions by remember { mutableStateOf<Set<String>>(emptySet()) }
    var requestedPermissions by remember { mutableStateOf<Set<String>>(emptySet()) }
    var backgroundReadAvailable by remember { mutableStateOf(false) }
    val permissionLauncher = rememberLauncherForActivityResult(
        PermissionController.createRequestPermissionResultContract(HealthConnectAccess.PROVIDER_PACKAGE_NAME),
    ) { granted ->
        grantedPermissions = granted
        status = if (requestedPermissions.all { it in granted }) "Requested access was granted." else "Only the granted data types will be synced."
    }

    fun refreshPermissions() {
        if (availability != HealthConnectAvailability.AVAILABLE) return
        scope.launch {
            val snapshot = HealthConnectAccess.permissionSnapshot(HealthConnectClient.getOrCreate(context))
            grantedPermissions = snapshot.granted
            backgroundReadAvailable = snapshot.backgroundReadAvailable
        }
    }

    LaunchedEffect(availability) {
        refreshPermissions()
        if (profileId.isBlank()) {
            profileId = Member2ConfigurationStore(context).load()?.userId?.toString() ?: ""
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Health Connect & sensor sync", style = MaterialTheme.typography.headlineSmall)
        Text("Wellness data only. This module preserves source, device and quality context; it does not diagnose medical conditions.")

        when (availability) {
            HealthConnectAvailability.AVAILABLE -> {
                Text("Health Connect is available.", color = MaterialTheme.colorScheme.primary)
                OutlinedTextField(
                    value = profileId,
                    onValueChange = { profileId = it.filter(Char::isDigit) },
                    label = { Text("Local M1 profile ID (development only)") },
                    supportingText = { Text("Saved locally after the first successful configuration; M1 can later supply the active profile automatically.") },
                    modifier = Modifier.fillMaxWidth(),
                )
                Button(
                    onClick = {
                        val client = HealthConnectClient.getOrCreate(context)
                        requestedPermissions = HealthConnectAccess.coreReadPermissions()
                        permissionLauncher.launch(requestedPermissions)
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Allow core activity, heart and sleep data") }
                OutlinedButton(
                    onClick = {
                        val client = HealthConnectClient.getOrCreate(context)
                        requestedPermissions = HealthConnectAccess.optionalMeasurementPermissions(client)
                        permissionLauncher.launch(requestedPermissions)
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Choose optional SpO₂, respiration and skin temperature") }
                OutlinedButton(
                    onClick = {
                        requestedPermissions = setOf(HealthConnectAccess.optionalBackgroundPermission())
                        permissionLauncher.launch(requestedPermissions)
                    },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = backgroundReadAvailable,
                ) { Text("Allow background sync") }
                Text("Granted permissions: ${grantedPermissions.size}", style = MaterialTheme.typography.bodySmall)

                Button(
                    onClick = {
                        val id = profileId.toIntOrNull()
                        if (id == null || id <= 0) {
                            status = "Enter the existing M1 health-profile user ID first."
                        } else {
                            scope.launch {
                                try {
                                    Member2Runtime.configureLocalProfileBackend(
                                        context,
                                        BuildConfig.API_BASE_URL,
                                        id,
                                    )
                                    val summary = Member2Runtime.sync(context)
                                    status = if (summary.failedTypes.isEmpty()) {
                                        "Sync complete: ${summary.upserted} readings uploaded; ${summary.deleted} deletions applied."
                                    } else {
                                        "Sync incomplete for ${summary.failedTypes.joinToString()}. Completed record types: ${summary.upserted} readings. Source data is retained; review the backend contract before retrying."
                                    }
                                } catch (error: CancellationException) {
                                    throw error
                                } catch (error: Exception) {
                                    status = "Sync did not complete: ${error.message ?: "check backend and permissions"}"
                                }
                            }
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Sync now") }
                OutlinedButton(
                    onClick = {
                        scope.launch {
                            try {
                                SensorSyncScheduler.enable(context)
                                status = "Background sync is scheduled while permission remains granted."
                            } catch (error: CancellationException) {
                                throw error
                            } catch (error: Exception) {
                                status = "Background sync unavailable: ${error.message ?: "grant permission first"}"
                            }
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Enable background sync") }
                OutlinedButton(
                    onClick = {
                        scope.launch {
                            Member2Runtime.disconnect(context)
                            val result = HealthConnectDisconnect.execute(
                                client = HealthConnectClient.getOrCreate(context),
                                tokenStore = SyncTokenStore(context),
                                cancelBackgroundWork = { SensorSyncScheduler.disable(context) },
                            )
                            status = if (result.complete) "Disconnected: local sync state and permissions were cleared." else "Disconnect completed partially; open Health Connect to verify access."
                            refreshPermissions()
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Disconnect and clear local sync state") }
                OutlinedButton(
                    onClick = {
                        context.startActivity(HealthConnectClient.getHealthConnectManageDataIntent(context))
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Manage Health Connect access") }
                OutlinedButton(
                    onClick = {
                        context.startActivity(Intent(context, CameraQualityActivity::class.java))
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Open research camera quality check") }
            }
            HealthConnectAvailability.UPDATE_REQUIRED -> Text("Update Health Connect before connecting a device.")
            HealthConnectAvailability.UNAVAILABLE -> Text("Health Connect is unavailable on this device.")
        }
        Text(status, style = MaterialTheme.typography.bodyMedium)
        Spacer(Modifier.height(4.dp))
        OutlinedButton(onClick = onNavigateBack, modifier = Modifier.fillMaxWidth()) { Text("Back") }
    }
}
