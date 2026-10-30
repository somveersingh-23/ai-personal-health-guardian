package com.healthguardian.app.feature.sensors.camera

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/** Research-only live preview used to assess lighting, blur and motion. */
class CameraQualityActivity : ComponentActivity() {
    private lateinit var executor: ExecutorService
    private lateinit var previewView: PreviewView
    private lateinit var statusView: TextView

    private val permissionLauncher = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) startCamera() else statusView.text = "Camera permission was not granted."
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        executor = Executors.newSingleThreadExecutor()
        previewView = PreviewView(this)
        statusView = TextView(this).apply {
            setTextColor(Color.WHITE)
            setBackgroundColor(0x99000000.toInt())
            setPadding(24, 24, 24, 24)
            text = "Checking capture quality only — no image is saved or interpreted as a vital sign."
        }
        setContentView(FrameLayout(this).apply {
            addView(previewView, FrameLayout.LayoutParams(-1, -1))
            addView(statusView, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM))
        })
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            permissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private fun startCamera() {
        val pendingProvider = ProcessCameraProvider.getInstance(this)
        pendingProvider.addListener({
            if (isDestroyed || isFinishing) return@addListener
            try {
            val provider = pendingProvider.get()
            if (!provider.hasCamera(CameraSelector.DEFAULT_BACK_CAMERA)) {
                statusView.text = "A back camera is unavailable on this device."
                return@addListener
            }
            val preview = Preview.Builder().build().also { it.surfaceProvider = previewView.surfaceProvider }
            val analysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also { it.setAnalyzer(executor, CameraQualityAnalyzer { result -> runOnUiThread { statusView.text = result.message } }) }
            provider.unbindAll()
            provider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
            } catch (_: Exception) {
                statusView.text = "Camera could not be started. Close this screen and check camera access."
            }
        }, ContextCompat.getMainExecutor(this))
    }

    override fun onDestroy() {
        executor.shutdownNow()
        super.onDestroy()
    }
}
