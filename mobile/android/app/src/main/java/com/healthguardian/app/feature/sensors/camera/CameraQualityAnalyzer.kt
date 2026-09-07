package com.healthguardian.app.feature.sensors.camera

import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * On-device capture-quality gate for a future, consented camera research flow.
 * It neither estimates nor labels a vital sign, and it never persists frames.
 */
data class CameraQualityResult(
    val acceptable: Boolean,
    val meanLuma: Double,
    val contrast: Double,
    val blurScore: Double,
    val motionScore: Double?,
    val clippedFraction: Double,
    val reasons: List<String>,
) {
    val message: String = if (acceptable) {
        "Capture quality acceptable. No health measurement is inferred."
    } else {
        reasons.joinToString(prefix = "Adjust capture: ")
    }
}

class CameraQualityAnalyzer(
    private val listener: (CameraQualityResult) -> Unit,
) : ImageAnalysis.Analyzer {
    private var previous: DoubleArray? = null

    override fun analyze(image: ImageProxy) {
        try {
            val plane = image.planes.firstOrNull() ?: return
            val width = 32
            val height = 32
            val values = DoubleArray(width * height)
            val buffer = plane.buffer
            for (gridY in 0 until height) {
                val y = gridY * (image.height - 1) / (height - 1)
                for (gridX in 0 until width) {
                    val x = gridX * (image.width - 1) / (width - 1)
                    val index = y * plane.rowStride + x * plane.pixelStride
                    values[gridY * width + gridX] = (buffer.get(index).toInt() and 0xff) / 255.0
                }
            }
            listener(CameraQualityScorer.evaluate(values, width, height, previous))
            previous = values
        } finally {
            image.close()
        }
    }
}

object CameraQualityScorer {
    fun evaluate(
        values: DoubleArray,
        width: Int,
        height: Int,
        previous: DoubleArray? = null,
    ): CameraQualityResult {
        require(width >= 3 && height >= 3 && values.size == width * height)
        require(values.all { it in 0.0..1.0 })
        require(previous == null || previous.size == values.size)
        val mean = values.average()
        val contrast = sqrt(values.sumOf { (it - mean) * (it - mean) } / values.size)
        val clipped = values.count { it <= 0.03 || it >= 0.97 }.toDouble() / values.size
        val blur = laplacianVariance(values, width, height)
        val motion = previous?.let { old -> values.indices.sumOf { abs(values[it] - old[it]) } / values.size }
        val reasons = buildList {
            if (mean !in 0.18..0.90) add("improve lighting")
            if (contrast < 0.025) add("increase contrast or reposition")
            if (blur < 0.0007) add("hold the device steady and refocus")
            if (motion != null && motion > 0.10) add("reduce movement")
            if (clipped > 0.45) add("avoid over- or under-exposure")
        }
        return CameraQualityResult(reasons.isEmpty(), mean, contrast, blur, motion, clipped, reasons)
    }

    private fun laplacianVariance(values: DoubleArray, width: Int, height: Int): Double {
        val responses = mutableListOf<Double>()
        for (y in 1 until height - 1) for (x in 1 until width - 1) {
            val center = values[y * width + x]
            responses += values[(y - 1) * width + x] + values[(y + 1) * width + x] +
                values[y * width + x - 1] + values[y * width + x + 1] - 4 * center
        }
        val mean = responses.average()
        return responses.sumOf { (it - mean) * (it - mean) } / responses.size
    }
}
