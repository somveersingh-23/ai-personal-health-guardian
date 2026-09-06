plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("com.google.devtools.ksp")
    id("com.google.dagger.hilt.android")
}

android {
    namespace = "com.healthguardian.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.healthguardian.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner =
            "androidx.test.runner.AndroidJUnitRunner"

        vectorDrawables {
            useSupportLibrary = true
        }

        buildConfigField(
            "String",
            "API_BASE_URL",
            "\"http://10.0.2.2:8000/\""
        )
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true

            proguardFiles(
                getDefaultProguardFile(
                    "proguard-android-optimize.txt"
                ),
                "proguard-rules.pro"
            )

            buildConfigField(
                "String",
                "API_BASE_URL",
                "\"https://your-production-api.com/\""
            )
        }

        debug {
            isMinifyEnabled = false

            buildConfigField(
                "String",
                "API_BASE_URL",
                "\"http://10.0.2.2:8000/\""
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
            excludes += "/META-INF/DEPENDENCIES"
        }
    }
}

dependencies {

    // ============================================================
    // CORE ANDROID
    // ============================================================

    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)


    // ============================================================
    // JETPACK COMPOSE
    // ============================================================

    implementation(platform(libs.androidx.compose.bom))

    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)

    implementation(
        "androidx.compose.material:material-icons-extended"
    )


    // ============================================================
    // NAVIGATION
    // ============================================================

    implementation(
        "androidx.navigation:navigation-compose:2.8.0"
    )


    // ============================================================
    // LIFECYCLE / VIEWMODEL
    // ============================================================

    implementation(
        "androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6"
    )

    implementation(
        "androidx.lifecycle:lifecycle-runtime-compose:2.8.6"
    )


    // ============================================================
    // COROUTINES
    // ============================================================

    implementation(
        "org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0"
    )

    implementation(
        "org.jetbrains.kotlinx:kotlinx-coroutines-core:1.9.0"
    )


    // ============================================================
    // RETROFIT
    // ============================================================

    implementation(
        "com.squareup.retrofit2:retrofit:2.11.0"
    )

    implementation(
        "com.squareup.retrofit2:converter-kotlinx-serialization:2.11.0"
    )


    // ============================================================
    // OKHTTP
    // ============================================================

    implementation(
        "com.squareup.okhttp3:okhttp:4.12.0"
    )

    implementation(
        "com.squareup.okhttp3:logging-interceptor:4.12.0"
    )


    // ============================================================
    // KOTLIN SERIALIZATION
    // ============================================================

    implementation(
        "org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3"
    )


    // ============================================================
    // HILT
    // KSP - NO KAPT
    // ============================================================

    implementation(
        "com.google.dagger:hilt-android:2.53.1"
    )

    ksp(
        "com.google.dagger:hilt-android-compiler:2.53.1"
    )

    implementation(
        "androidx.hilt:hilt-navigation-compose:1.2.0"
    )


    // ============================================================
    // SECURITY
    // ============================================================

    implementation(
        "androidx.security:security-crypto:1.1.0-alpha06"
    )


    // ============================================================
    // SPLASH SCREEN
    // ============================================================

    implementation(
        "androidx.core:core-splashscreen:1.0.1"
    )


    // ============================================================
    // UNIT TESTING
    // ============================================================

    testImplementation(libs.junit)

    testImplementation(
        "junit:junit:4.13.2"
    )


    // ============================================================
    // ANDROID TESTING
    // ============================================================

    androidTestImplementation(
        platform(libs.androidx.compose.bom)
    )

    androidTestImplementation(
        libs.androidx.compose.ui.test.junit4
    )

    androidTestImplementation(
        libs.androidx.espresso.core
    )

    androidTestImplementation(
        libs.androidx.junit
    )


    // ============================================================
    // DEBUG
    // ============================================================

    debugImplementation(
        libs.androidx.compose.ui.tooling
    )

    debugImplementation(
        libs.androidx.compose.ui.test.manifest
    )
}