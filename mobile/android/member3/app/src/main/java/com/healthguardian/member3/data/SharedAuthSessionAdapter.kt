package com.healthguardian.member3.data

/** Adapter seam for M1 authentication without importing M1-owned classes. */
class SharedAuthSessionAdapter(
    private val userIdProvider: () -> String,
    private val accessTokenProvider: () -> String?,
    private val sessionUpdater: (String, String?) -> Unit = { _, _ -> },
    private val sessionClearer: () -> Unit = {},
) : SessionManager {
    override val currentUserId: String get() = userIdProvider().trim()
    override val token: String? get() = accessTokenProvider()?.trim()?.ifBlank { null }
    override val isAuthenticated: Boolean
        get() = currentUserId.isNotBlank() && !token.isNullOrBlank()

    override fun updateSession(userId: String, token: String?) =
        sessionUpdater(userId.trim(), token?.trim())

    override fun clearSession() = sessionClearer()
}
