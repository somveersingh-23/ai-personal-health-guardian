package com.healthguardian.member3

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import com.healthguardian.member3.data.InMemorySessionManager
import com.healthguardian.member3.data.Member3ApiClient
import com.healthguardian.member3.data.Member3Repository
import com.healthguardian.member3.ui.GuardianApp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // The shared authentication module must populate this after login.
        // The standalone app deliberately starts unauthenticated.
        val sessionManager = InMemorySessionManager()
        val apiClient = Member3ApiClient(
            baseUrl = BuildConfig.MEMBER3_API_BASE_URL,
            sessionManager = sessionManager,
            allowEmulatorCleartext = BuildConfig.DEBUG,
        )
        val repository = Member3Repository(apiClient)
        setContent {
            MaterialTheme(colorScheme = lightColorScheme()) {
                GuardianApp(repository, sessionManager)
            }
        }
    }
}
