package com.healthguardian.sensor.sync

import com.healthguardian.sensor.network.AccessTokenProvider
import org.junit.After
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class Member2RuntimeTest {
    @After
    fun clearRuntime() {
        Member2Runtime.clear()
    }

    @Test
    fun authenticatedBackendConfigurationRequiresHttps() {
        val tokenProvider = AccessTokenProvider { "test-token" }
        var failed = false

        try {
            Member2Runtime.configureAuthenticatedBackend("http://example.test", tokenProvider)
        } catch (_: IllegalArgumentException) {
            failed = true
        }

        assertTrue(failed)
        assertFalse(Member2Runtime.isConfigured())

        Member2Runtime.configureAuthenticatedBackend("https://example.test", tokenProvider)
        assertTrue(Member2Runtime.isConfigured())
    }
}
