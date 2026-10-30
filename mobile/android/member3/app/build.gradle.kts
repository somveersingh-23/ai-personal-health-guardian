plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

fun buildConfigString(value: String): String =
    "\"${value.replace("\\", "\\\\").replace("\"", "\\\"")}\""

val releaseApiBaseUrl = providers.gradleProperty("member3ApiBaseUrl").orNull.orEmpty()

android {
    namespace = "com.healthguardian.member3"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.healthguardian.member3"
        minSdk = 23
        targetSdk = 37
        versionCode = 1
        versionName = "1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    buildTypes {
        debug {
            // Cleartext is enabled only by src/debug/AndroidManifest.xml for
            // the Android-emulator loopback host.
            buildConfigField("String", "MEMBER3_API_BASE_URL", "\"http://10.0.2.2:8000\"")
        }
        release {
            // CI may build an unsigned release with an empty value, but the
            // client rejects it at startup. A distributable release therefore
            // requires -Pmember3ApiBaseUrl=https://api.example.com.
            buildConfigField("String", "MEMBER3_API_BASE_URL", buildConfigString(releaseApiBaseUrl))
        }
    }
    buildFeatures { compose = true; buildConfig = true }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.08.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.11.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.11.0")
    implementation("androidx.navigation:navigation-compose:2.9.5")
    debugImplementation("androidx.compose.ui:ui-tooling")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
