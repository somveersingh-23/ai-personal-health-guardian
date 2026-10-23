package com.healthguardian.app.data.repository

import com.healthguardian.app.data.mapper.toDomain
import com.healthguardian.app.data.remote.api.ApiService
import com.healthguardian.app.domain.model.DigitalTwin
import com.healthguardian.app.domain.repository.DigitalTwinRepository
import dagger.hilt.android.scopes.ViewModelScoped
import retrofit2.HttpException
import java.io.IOException
import javax.inject.Inject

@ViewModelScoped
class DigitalTwinRepositoryImpl @Inject constructor(
    private val apiService: ApiService
) : DigitalTwinRepository {

    override suspend fun getDigitalTwin(userId: Int): DigitalTwin {
        if (userId <= 0) throw IllegalArgumentException("A valid user ID is required.")

        val response = apiService.getMember1DigitalTwin(userId)
        if (!response.isSuccessful) {
            val detail = when (response.code()) {
                404 -> "No Digital Twin data found for this user. Run the ML pipeline first."
                503 -> "Health intelligence files are not ready yet."
                else -> "Health server returned HTTP ${response.code()}."
            }
            throw IOException(detail, HttpException(response))
        }

        val body = response.body()
            ?: throw IOException("The health server returned an empty response.")
        return body.toDomain()
    }
}
