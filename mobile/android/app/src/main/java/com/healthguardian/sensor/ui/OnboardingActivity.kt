package com.healthguardian.sensor.ui

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity

class OnboardingActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}
