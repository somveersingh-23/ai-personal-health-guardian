package com.healthguardian.sensor.ui

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.lifecycleScope
import androidx.core.net.toUri
import com.healthguardian.sensor.R
import com.healthguardian.sensor.camera.CameraQualityActivity
import com.healthguardian.sensor.healthconnect.HealthConnectAccess
import com.healthguardian.sensor.healthconnect.HealthConnectAvailability
import com.healthguardian.sensor.healthconnect.HealthConnectDisconnect
import com.healthguardian.sensor.healthconnect.PermissionSnapshot
import com.healthguardian.sensor.healthconnect.SyncTokenStore
import com.healthguardian.sensor.sync.Member2Runtime
import com.healthguardian.sensor.sync.BackgroundSyncPolicy
import com.healthguardian.sensor.sync.SensorSyncScheduler
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private lateinit var root: LinearLayout
    private lateinit var statusView: TextView
    private lateinit var pauseButton: Button
    private lateinit var backgroundButton: Button
    private lateinit var historyButton: Button
    private var client: HealthConnectClient? = null

    private val permissionLauncher = registerForActivityResult(
        PermissionController.createRequestPermissionResultContract(),
    ) { refreshState() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(40, 56, 40, 56)
        }
        statusView = TextView(this).apply {
            textSize = 18f
            setTextColor(Color.rgb(20, 55, 48))
        }
        root.addView(TextView(this).apply {
            setText(R.string.sensor_title)
            textSize = 26f
            setTextColor(Color.rgb(0, 92, 78))
        })
        root.addView(TextView(this).apply {
            setText(R.string.wellness_disclaimer)
            textSize = 15f
            setPadding(0, 12, 0, 28)
        })
        root.addView(statusView)

        root.addButton(getString(R.string.grant_required_access)) {
            client?.let { permissionLauncher.launch(HealthConnectAccess.requiredPermissions(it)) }
        }
        backgroundButton = root.addButton(getString(R.string.grant_background_access)) {
            client?.let {
                permissionLauncher.launch(setOf(HealthConnectAccess.optionalBackgroundPermission()))
            }
        }
        historyButton = root.addButton(getString(R.string.grant_history_access)) {
            client?.let {
                permissionLauncher.launch(setOf(HealthConnectAccess.optionalHistoryPermission()))
            }
        }
        root.addButton(getString(R.string.sync_now)) {
            lifecycleScope.launch {
                statusView.setText(R.string.sync_in_progress)
                statusView.text = try {
                    val summary = Member2Runtime.sync(this@MainActivity)
                    getString(
                        R.string.sync_complete,
                        summary.upserted,
                        summary.deleted,
                        summary.revokedTypes.size,
                    )
                } catch (cancelled: CancellationException) {
                    throw cancelled
                } catch (error: Exception) {
                    getString(R.string.sync_unavailable, error.message.orEmpty())
                }
            }
        }
        pauseButton = root.addButton(getString(R.string.pause_sync)) {
            lifecycleScope.launch {
                val store = SyncTokenStore(this@MainActivity)
                val paused = !store.isPaused()
                store.setPaused(paused)
                val snapshot = try {
                    client?.let { HealthConnectAccess.permissionSnapshot(it) }
                } catch (cancelled: CancellationException) {
                    throw cancelled
                } catch (_: Exception) {
                    null
                }
                applyBackgroundSyncPolicy(paused, snapshot)
                updatePauseButton(paused)
            }
        }
        root.addButton(getString(R.string.disconnect_health_connect)) {
            lifecycleScope.launch {
                val connectedClient = client ?: run {
                    statusView.setText(R.string.health_connect_unavailable)
                    return@launch
                }
                statusView.setText(R.string.disconnect_in_progress)
                val result = HealthConnectDisconnect.execute(
                    client = connectedClient,
                    tokenStore = SyncTokenStore(this@MainActivity),
                    cancelBackgroundWork = {
                        SensorSyncScheduler.disable(this@MainActivity)
                    },
                )
                statusView.setText(
                    if (result.complete) {
                        R.string.disconnected_explanation
                    } else {
                        R.string.disconnect_partial_explanation
                    },
                )
                updatePauseButton(true)
                if (!result.permissionsRevoked) {
                    openHealthConnectSettings()
                }
            }
        }
        root.addButton(getString(R.string.manage_health_connect)) {
            openHealthConnectSettings()
        }
        root.addButton(getString(R.string.open_camera_quality)) {
            startActivity(Intent(this, CameraQualityActivity::class.java))
        }
        root.addButton(getString(R.string.read_privacy_rationale)) {
            startActivity(Intent(this, PrivacyRationaleActivity::class.java))
        }

        setContentView(ScrollView(this).apply { addView(root) })
        initializeHealthConnect()
    }

    override fun onResume() {
        super.onResume()
        refreshState()
    }

    private fun initializeHealthConnect() {
        when (HealthConnectAccess.availability(this)) {
            HealthConnectAvailability.AVAILABLE -> {
                client = HealthConnectClient.getOrCreate(this)
                refreshState()
            }
            HealthConnectAvailability.UPDATE_REQUIRED -> {
                statusView.setText(R.string.health_connect_update_required)
                root.addButton(getString(R.string.open_health_connect_store)) {
                    val packageName = HealthConnectAccess.PROVIDER_PACKAGE_NAME
                    startActivity(Intent(Intent.ACTION_VIEW, "market://details?id=$packageName".toUri()))
                }
            }
            HealthConnectAvailability.UNAVAILABLE -> {
                statusView.setText(R.string.health_connect_unavailable)
            }
        }
    }

    private fun refreshState() {
        val connectedClient = client ?: return
        lifecycleScope.launch {
            val snapshot = try {
                HealthConnectAccess.permissionSnapshot(connectedClient)
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Exception) {
                statusView.text = getString(
                    R.string.permission_state_error,
                    error.message.orEmpty(),
                )
                return@launch
            }
            statusView.text = getString(
                R.string.permission_state,
                getString(if (snapshot.allRequiredGranted) R.string.access_granted else R.string.access_incomplete),
                snapshot.granted.intersect(snapshot.required).size,
                snapshot.required.size,
                getString(if (snapshot.backgroundReadAvailable) R.string.available else R.string.unsupported),
                getString(if (snapshot.historyReadAvailable) R.string.available else R.string.unsupported),
            )
            backgroundButton.isEnabled = snapshot.backgroundReadAvailable
            historyButton.isEnabled = snapshot.historyReadAvailable
            val paused = SyncTokenStore(this@MainActivity).isPaused()
            applyBackgroundSyncPolicy(paused, snapshot)
            updatePauseButton(paused)
        }
    }

    private suspend fun applyBackgroundSyncPolicy(
        paused: Boolean,
        snapshot: PermissionSnapshot?,
    ) {
        val shouldEnable = BackgroundSyncPolicy.shouldSchedule(
            paused = paused,
            grantedPermissions = snapshot?.granted.orEmpty(),
        )
        try {
            if (shouldEnable) {
                SensorSyncScheduler.enable(this@MainActivity)
            } else {
                SensorSyncScheduler.disable(this@MainActivity)
            }
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (_: Exception) {
            statusView.setText(R.string.background_schedule_error)
        }
    }

    private fun openHealthConnectSettings() {
        runCatching { startActivity(Intent(HealthConnectClient.ACTION_HEALTH_CONNECT_SETTINGS)) }
    }

    private fun updatePauseButton(paused: Boolean) {
        pauseButton.setText(if (paused) R.string.resume_sync else R.string.pause_sync)
    }

    private fun LinearLayout.addButton(label: String, action: (View) -> Unit): Button =
        Button(context).apply {
            text = label
            isAllCaps = false
            setOnClickListener { action(it) }
            this@addButton.addView(this)
        }
}
