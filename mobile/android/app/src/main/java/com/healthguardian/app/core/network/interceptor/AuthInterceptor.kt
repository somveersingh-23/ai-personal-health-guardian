package com.healthguardian.app.core.network.interceptor

import com.healthguardian.app.core.network.ApiConstants
import com.healthguardian.app.core.security.SecureTokenStore
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor(
    private val secureTokenStore: SecureTokenStore
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()

        val publicPaths = listOf("/api/v1/auth/login", "/api/v1/auth/register")

        val isPublicEndpoint = publicPaths.any { path ->
            originalRequest.url.encodedPath.contains(path, ignoreCase = true)
        }

        if (isPublicEndpoint) {
            return chain.proceed(originalRequest)
        }

        val accessToken = runBlocking {
            secureTokenStore.getAccessToken()
        }

        if (accessToken.isNullOrBlank()) {
            return chain.proceed(originalRequest)
        }

        val authenticatedRequest = originalRequest.newBuilder()
            .header(
                ApiConstants.Headers.AUTHORIZATION,
                "${ApiConstants.Headers.BEARER_PREFIX}$accessToken"
            )
            .header(ApiConstants.Headers.ACCEPT, ApiConstants.Headers.ACCEPT_JSON)
            .header(ApiConstants.Headers.CONTENT_TYPE, ApiConstants.Headers.CONTENT_TYPE_JSON)
            .build()

        return chain.proceed(authenticatedRequest)
    }
}