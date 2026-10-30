package com.healthguardian.app.feature.sensors.sync

import android.content.Context
import androidx.datastore.preferences.core.MutablePreferences
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flow

private val Context.member2ConfigurationDataStore by preferencesDataStore(
    name = "member2_sensor_configuration",
)

data class LocalProfileConfiguration(
    val userId: Int,
    val baseUrl: String,
)

internal interface Member2ConfigurationStorage {
    val data: Flow<Preferences>
    suspend fun edit(transform: suspend (MutablePreferences) -> Unit)
}

private class DataStoreMember2ConfigurationStorage(
    private val context: Context,
) : Member2ConfigurationStorage {
    override val data: Flow<Preferences> = context.member2ConfigurationDataStore.data

    override suspend fun edit(transform: suspend (MutablePreferences) -> Unit) {
        context.member2ConfigurationDataStore.edit(transform)
    }
}

internal class InMemoryMember2ConfigurationStorage : Member2ConfigurationStorage {
    private var preferences: Preferences = emptyPreferences()

    override val data: Flow<Preferences> = flow { emit(preferences) }

    override suspend fun edit(transform: suspend (MutablePreferences) -> Unit) {
        val mutable = preferences.toMutablePreferences()
        transform(mutable)
        preferences = mutable.toPreferences()
    }
}

/**
 * Persists only the local profile binding needed to rebuild the M2 transport.
 * Health measurements and Health Connect change tokens are not stored here.
 */
internal class Member2ConfigurationStore(
    private val storage: Member2ConfigurationStorage,
) {
    constructor(context: Context) : this(DataStoreMember2ConfigurationStorage(context))

    suspend fun load(): LocalProfileConfiguration? {
        val preferences = storage.data.first()
        val userId = preferences[USER_ID] ?: return null
        val baseUrl = preferences[BASE_URL]?.trimEnd('/') ?: return null
        return if (userId > 0 && baseUrl.isNotBlank()) {
            LocalProfileConfiguration(userId, baseUrl)
        } else {
            null
        }
    }

    suspend fun save(configuration: LocalProfileConfiguration) {
        require(configuration.userId > 0) { "local profile ID must be positive" }
        val normalizedUrl = configuration.baseUrl.trimEnd('/')
        require(normalizedUrl.isNotBlank()) { "backend URL must not be blank" }
        storage.edit {
            it[USER_ID] = configuration.userId
            it[BASE_URL] = normalizedUrl
        }
    }

    suspend fun clear() {
        storage.edit {
            it.remove(USER_ID)
            it.remove(BASE_URL)
        }
    }

    private companion object {
        val USER_ID = intPreferencesKey("local_profile_user_id")
        val BASE_URL = stringPreferencesKey("sensor_backend_base_url")
    }
}
