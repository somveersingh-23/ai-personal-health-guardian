package com.healthguardian.sensor.healthconnect

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import java.nio.ByteBuffer
import java.security.KeyStore
import java.security.MessageDigest
import java.time.Instant
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first

private val Context.healthSyncDataStore by preferencesDataStore(name = "health_connect_sync")

data class StoredSyncState(val token: String, val lastSuccessfulSyncAt: Instant)

interface TokenStoreStorage {
    val data: Flow<Preferences>
    suspend fun edit(transform: suspend (androidx.datastore.preferences.core.MutablePreferences) -> Unit)
}

class DataStoreTokenStorage(private val context: Context) : TokenStoreStorage {
    override val data: Flow<Preferences> = context.healthSyncDataStore.data
    override suspend fun edit(transform: suspend (androidx.datastore.preferences.core.MutablePreferences) -> Unit) {
        context.healthSyncDataStore.edit(transform)
    }
}

class InMemoryTokenStorage : TokenStoreStorage {
    private var preferences: Preferences = emptyPreferences()

    override val data: Flow<Preferences> = kotlinx.coroutines.flow.flow { emit(preferences) }

    override suspend fun edit(transform: suspend (androidx.datastore.preferences.core.MutablePreferences) -> Unit) {
        val mutable = preferences.toMutablePreferences()
        transform(mutable)
        preferences = mutable.toPreferences()
    }
}

class SyncTokenStore internal constructor(
    private val storage: TokenStoreStorage,
    private val cipher: SyncTokenCipher,
) {
    constructor(context: Context) : this(
        DataStoreTokenStorage(context),
        AndroidKeyStoreSyncTokenCipher,
    )

    suspend fun load(recordType: String): StoredSyncState? {
        val preferences = storage.data.first()
        val encrypted = preferences[stringPreferencesKey("token_${keySuffix(recordType)}")] ?: return null
        val lastSync = preferences[longPreferencesKey("time_${keySuffix(recordType)}")] ?: return null
        return runCatching {
            val decrypted = cipher.decrypt(encrypted, recordType)
            StoredSyncState(decrypted, Instant.ofEpochMilli(lastSync))
        }.getOrNull()
    }

    suspend fun save(recordType: String, token: String, at: Instant) {
        require(token.isNotBlank()) { "sync token must not be blank" }
        storage.edit { preferences ->
            preferences[stringPreferencesKey("token_${keySuffix(recordType)}")] =
                cipher.encrypt(token, recordType)
            preferences[longPreferencesKey("time_${keySuffix(recordType)}")] = at.toEpochMilli()
        }
    }

    suspend fun clear(recordType: String) {
        storage.edit { preferences ->
            preferences.remove(stringPreferencesKey("token_${keySuffix(recordType)}"))
            preferences.remove(longPreferencesKey("time_${keySuffix(recordType)}"))
        }
    }

    suspend fun clearAll() {
        storage.edit { preferences ->
            val keysToRemove = preferences.asMap().keys.filter {
                it.name.startsWith("token_") || it.name.startsWith("time_")
            }
            keysToRemove.forEach { preferences.remove(it) }
        }
    }

    suspend fun isPaused(): Boolean =
        storage.data.first()[booleanPreferencesKey("sync_paused")] ?: false

    suspend fun setPaused(paused: Boolean) {
        storage.edit { it[booleanPreferencesKey("sync_paused")] = paused }
    }

    private fun keySuffix(recordType: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(recordType.toByteArray(Charsets.UTF_8))
        return digest.take(12).joinToString("") { "%02x".format(it) }
    }
}

internal interface SyncTokenCipher {
    fun encrypt(value: String, recordType: String): String

    fun decrypt(value: String, recordType: String): String
}

internal abstract class AesGcmSyncTokenCipher : SyncTokenCipher {
    protected abstract fun secretKey(): SecretKey

    final override fun encrypt(value: String, recordType: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val iv = cipher.iv
        require(iv.size == IV_LENGTH) { "unexpected AES-GCM IV length" }
        cipher.updateAAD(recordType.toByteArray(Charsets.UTF_8))
        val ciphertext = cipher.doFinal(value.toByteArray(Charsets.UTF_8))

        val payload = ByteBuffer.allocate(1 + 1 + iv.size + ciphertext.size)
            .put(CIPHER_VERSION)
            .put(iv.size.toByte())
            .put(iv)
            .put(ciphertext)
            .array()
        return Base64.getEncoder().encodeToString(payload)
    }

    final override fun decrypt(value: String, recordType: String): String {
        val payload = ByteBuffer.wrap(Base64.getDecoder().decode(value))
        require(payload.remaining() >= MINIMUM_PAYLOAD_BYTES) { "encrypted token payload is truncated" }
        val version = payload.get()
        require(version == CIPHER_VERSION) { "unsupported cipher version: $version" }
        val ivLength = payload.get().toInt() and 0xFF
        require(ivLength == IV_LENGTH && payload.remaining() > ivLength) {
            "invalid encrypted token payload"
        }
        val iv = ByteArray(ivLength).also(payload::get)
        val ciphertext = ByteArray(payload.remaining()).also(payload::get)

        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(GCM_TAG_LENGTH, iv))
        cipher.updateAAD(recordType.toByteArray(Charsets.UTF_8))
        return cipher.doFinal(ciphertext).toString(Charsets.UTF_8)
    }

    private companion object {
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val CIPHER_VERSION: Byte = 2
        const val GCM_TAG_LENGTH = 128
        const val IV_LENGTH = 12
        const val MINIMUM_PAYLOAD_BYTES = 1 + 1 + IV_LENGTH + (GCM_TAG_LENGTH / 8)
    }
}

internal object AndroidKeyStoreSyncTokenCipher : AesGcmSyncTokenCipher() {
    private const val ANDROID_KEY_STORE = "AndroidKeyStore"
    private const val KEY_ALIAS = "health_guardian_sync_token_v2"

    override fun secretKey(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEY_STORE).apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }

        val keyGenerator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            ANDROID_KEY_STORE,
        )
        keyGenerator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return keyGenerator.generateKey()
    }
}
