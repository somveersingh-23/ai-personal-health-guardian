package com.healthguardian.app.data.remote.api

import com.healthguardian.app.data.remote.dto.AuthResponse
import com.healthguardian.app.data.remote.dto.ChatRequest
import com.healthguardian.app.data.remote.dto.ChatResponse
import com.healthguardian.app.data.remote.dto.DashboardResponse
import com.healthguardian.app.data.remote.dto.HealthProfileRequest
import com.healthguardian.app.data.remote.dto.HealthProfileResponse
import com.healthguardian.app.data.remote.dto.HealthRecordRequest
import com.healthguardian.app.data.remote.dto.HealthRecordResponse
import com.healthguardian.app.data.remote.dto.InsightResponse
import com.healthguardian.app.data.remote.dto.LoginRequest
import com.healthguardian.app.data.remote.dto.RegisterRequest
import com.healthguardian.app.data.remote.dto.UserResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Query

interface ApiService {

    @POST("api/v1/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<AuthResponse>

    @POST("api/v1/auth/register")
    suspend fun register(@Body request: RegisterRequest): Response<AuthResponse>

    @POST("api/v1/auth/logout")
    suspend fun logout(): Response<Unit>

    @GET("api/v1/auth/me")
    suspend fun getCurrentUser(): Response<UserResponse>

    @GET("api/v1/profile")
    suspend fun getHealthProfile(): Response<HealthProfileResponse>

    @PUT("api/v1/profile/update")
    suspend fun updateHealthProfile(
        @Body request: HealthProfileRequest
    ): Response<HealthProfileResponse>

    @GET("api/v1/records")
    suspend fun getHealthRecords(
        @Query("type") type: String? = null,
        @Query("limit") limit: Int = 20
    ): Response<List<HealthRecordResponse>>

    @POST("api/v1/records")
    suspend fun createHealthRecord(
        @Body request: HealthRecordRequest
    ): Response<HealthRecordResponse>

    @POST("api/v1/ai/chat")
    suspend fun chat(
        @Body request: ChatRequest
    ): Response<ChatResponse>

    @GET("api/v1/insights")
    suspend fun getInsights(
        @Query("limit") limit: Int = 20
    ): Response<List<InsightResponse>>

    @GET("api/v1/dashboard")
    suspend fun getDashboard(): Response<DashboardResponse>
}