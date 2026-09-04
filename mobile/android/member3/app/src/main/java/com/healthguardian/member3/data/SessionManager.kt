package com.healthguardian.member3.data

interface SessionManager {
    val currentUserId: String
    val token: String?
    val isAuthenticated: Boolean
    fun updateSession(userId: String, token: String?)
    fun clearSession()
}

class InMemorySessionManager(
    private var userId: String = "",
    private var userToken: String? = null,
) : SessionManager {
    override val currentUserId: String
        get() = userId

    override val token: String?
        get() = userToken

    override val isAuthenticated: Boolean
        get() = userId.isNotBlank() && !userToken.isNullOrBlank()

    override fun updateSession(userId: String, token: String?) {
        this.userId = userId.trim()
        this.userToken = token?.trim()
    }

    override fun clearSession() {
        this.userId = ""
        this.userToken = null
    }
}
