package com.healthguardian.member3

import androidx.compose.runtime.Composable
import com.healthguardian.member3.data.InMemoryGuardianCache
import com.healthguardian.member3.data.LocalGuardianCache
import com.healthguardian.member3.data.Member3Gateway
import com.healthguardian.member3.data.Member3Repository
import com.healthguardian.member3.data.SessionManager
import com.healthguardian.member3.ui.GuardianApp

/**
 * Transport-neutral entry point for the shared M1/M2 Android app.
 *
 * M1 supplies its authenticated SessionManager adapter and Retrofit-backed
 * gateway; M2 remains responsible for sensor runtime configuration. M3 does
 * not import or duplicate either member's implementation.
 */
data class Member3Dependencies(
    val gateway: Member3Gateway,
    val sessionManager: SessionManager,
    val cache: LocalGuardianCache = InMemoryGuardianCache(),
)

@Composable
fun Member3Feature(dependencies: Member3Dependencies) {
    GuardianApp(
        repository = Member3Repository(dependencies.gateway, dependencies.cache),
        sessionManager = dependencies.sessionManager,
    )
}
