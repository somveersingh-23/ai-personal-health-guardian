package com.healthguardian.member3

import com.healthguardian.member3.data.InMemorySessionManager
import com.healthguardian.member3.data.SharedAuthSessionAdapter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SessionManagerTest {
    @Test
    fun configuredSessionIsAuthenticated() {
        val manager = InMemorySessionManager("user-1", "jwt-token")

        assertEquals("user-1", manager.currentUserId)
        assertEquals("jwt-token", manager.token)
        assertTrue(manager.isAuthenticated)
    }

    @Test
    fun updateSessionUpdatesCredentials() {
        val manager = InMemorySessionManager()
        manager.updateSession("new-user", "new-jwt")

        assertEquals("new-user", manager.currentUserId)
        assertEquals("new-jwt", manager.token)
        assertTrue(manager.isAuthenticated)
    }

    @Test
    fun userWithoutTokenIsNotAuthenticated() {
        val manager = InMemorySessionManager("user-1", null)

        assertFalse(manager.isAuthenticated)
    }

    @Test
    fun clearSessionResetsCredentials() {
        val manager = InMemorySessionManager("user-1", "jwt-token")
        manager.clearSession()

        assertEquals("", manager.currentUserId)
        assertNull(manager.token)
        assertFalse(manager.isAuthenticated)
    }

    @Test
    fun sharedAuthAdapterReadsM1OwnedSessionWithoutCopyingTokenState() {
        var userId = "42"
        var token: String? = "shared-jwt"
        val manager = SharedAuthSessionAdapter(
            userIdProvider = { userId },
            accessTokenProvider = { token },
            sessionClearer = { userId = ""; token = null },
        )

        assertTrue(manager.isAuthenticated)
        assertEquals("42", manager.currentUserId)
        manager.clearSession()
        assertFalse(manager.isAuthenticated)
    }
}
