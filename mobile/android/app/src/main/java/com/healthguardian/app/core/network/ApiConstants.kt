package com.healthguardian.app.core.network

import com.healthguardian.app.BuildConfig

object ApiConstants {
    const val BASE_URL = BuildConfig.API_BASE_URL
    const val CONNECT_TIMEOUT = 30L
    const val READ_TIMEOUT = 30L
    const val WRITE_TIMEOUT = 30L

    object Headers {
        const val CONTENT_TYPE = "Content-Type"
        const val AUTHORIZATION = "Authorization"
        const val ACCEPT = "Accept"
        const val CONTENT_TYPE_JSON = "application/json"
        const val ACCEPT_JSON = "application/json"
        const val BEARER_PREFIX = "Bearer "
    }
}