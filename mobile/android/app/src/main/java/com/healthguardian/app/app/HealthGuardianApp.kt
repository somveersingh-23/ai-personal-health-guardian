package com.healthguardian.app.app

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class HealthGuardianApp : Application() {

    override fun onCreate() {
        super.onCreate()
    }
}