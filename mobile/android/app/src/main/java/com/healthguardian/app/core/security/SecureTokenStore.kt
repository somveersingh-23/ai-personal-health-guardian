package com.healthguardian.app.core.security

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import android.content.SharedPreferences
import androidx.security.crypto.MasterKey
class SecureTokenStore(context: Context) {

    private val fileName = "auth_tokens_encrypted"
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val preferences: SharedPreferences =
        EncryptedSharedPreferences.create(
            context,
            "secure_tokens",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )

    companion object {
        private const val KEY_ACCESS_TOKEN = "access_token"
        private const val KEY_REFRESH_TOKEN = "refresh_token"
        private const val KEY_TOKEN_EXPIRY = "token_expiry"
    }

    suspend fun saveTokens(
        accessToken: String,
        refreshToken: String?,
        expiryTimestamp: Long?
    ) {
        preferences.edit()
            .putString(KEY_ACCESS_TOKEN, accessToken)
            .apply {
                refreshToken?.let { putString(KEY_REFRESH_TOKEN, it) }
                expiryTimestamp?.let { putLong(KEY_TOKEN_EXPIRY, it) }
            }
            .apply()
    }

    suspend fun getAccessToken(): String? {
        return preferences.getString(KEY_ACCESS_TOKEN, null)
    }

    suspend fun getRefreshToken(): String? {
        return preferences.getString(KEY_REFRESH_TOKEN, null)
    }

    suspend fun isAuthenticated(): Boolean {
        val token = getAccessToken()
        val expiry = preferences.getLong(KEY_TOKEN_EXPIRY, -1)
        val currentTime = System.currentTimeMillis()

        return !token.isNullOrBlank() && (expiry == -1L || expiry > currentTime)
    }

    suspend fun clearTokens() {
        preferences.edit().clear().apply()
    }
}