package com.healthguardian.app.core.ui

import androidx.annotation.StringRes
import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import com.healthguardian.app.R

/**
 * Sealed class for UI text that supports both string resources and plain strings
 * Useful for ViewModels that need to provide text without Android dependencies
 */
sealed class UiText {
    /**
     * Dynamic string value
     */
    data class DynamicString(val value: String) : UiText()

    /**
     * String resource with optional format arguments
     */
    data class StringResource(
        @StringRes val id: Int,
        val args: Array<Any> = arrayOf()
    ) : UiText()

    /**
     * Get string representation at runtime
     */
    @Composable
    fun asString(): String {
        return when (this) {
            is DynamicString -> value
            is StringResource -> stringResource(id = id, formatArgs = args)
        }
    }

    /**
     * Convert to string (for non-Composable contexts)
     */
    fun toString(context: android.content.Context): String {
        return when (this) {
            is DynamicString -> value
            is StringResource -> context.getString(id, *args)
        }
    }
}

/**
 * Common error messages as UiText
 */
object UiTexts {
    val errorNetwork = UiText.DynamicString("Network error. Please check your connection.")
    val errorUnknown = UiText.DynamicString("An unexpected error occurred")
    val errorTimeout = UiText.DynamicString("Request timed out. Please try again.")
    val errorNoInternet = UiText.DynamicString("No internet connection. Please check your network.")
    val errorServerError = UiText.DynamicString("Server error. Please try again later.")
    val errorUnauthorized = UiText.DynamicString("Session expired. Please login again.")
    val errorBadRequest = UiText.DynamicString("Invalid request. Please check your input.")
    val errorNotFound = UiText.DynamicString("Resource not found.")
    val errorForbidden = UiText.DynamicString("Access denied.")
    val errorConflict = UiText.DynamicString("Conflict. This resource already exists.")

    // Success messages
    val successSaved = UiText.DynamicString("Saved successfully")
    val successDeleted = UiText.DynamicString("Deleted successfully")
    val successUpdated = UiText.DynamicString("Updated successfully")
    val successCreated = UiText.DynamicString("Created successfully")

    // Validation messages
    val errorFieldRequired = UiText.DynamicString("This field is required")
    val errorInvalidEmail = UiText.DynamicString("Invalid email address")
    val errorPasswordTooShort = UiText.DynamicString("Password must be at least 8 characters")
    val errorPasswordsDontMatch = UiText.DynamicString("Passwords don't match")
    val errorInvalidPhone = UiText.DynamicString("Invalid phone number")

    // Empty states
    val emptyNoData = UiText.DynamicString("No data available")
    val emptyNoResults = UiText.DynamicString("No results found")
    val emptyNoRecords = UiText.DynamicString("No records yet")
    val emptyNoInsights = UiText.DynamicString("No insights yet")

    // Loading messages
    val loadingDefault = UiText.DynamicString("Loading...")
    val loadingSaving = UiText.DynamicString("Saving...")
    val loadingDeleting = UiText.DynamicString("Deleting...")
    val loadingSending = UiText.DynamicString("Sending...")
}

/**
 * Helper function to create a string resource UiText
 */
fun stringResource(@StringRes id: Int, vararg args: Any): UiText {
    return UiText.StringResource(id, args.toList().toTypedArray())
}
/**
 * Helper function to create a dynamic string UiText
 */
fun dynamicString(value: String): UiText {
    return UiText.DynamicString(value)
}

/**
 * Extension function to provide a default value if UiText is null
 */
fun UiText?.orDefault(default: UiText): UiText {
    return this ?: default
}

/**
 * Map UiText to another UiText
 */
fun UiText.map(transform: (String) -> String): UiText {
    return when (this) {
        is UiText.DynamicString -> UiText.DynamicString(transform(value))
        is UiText.StringResource -> this // Cannot transform string resources
    }
}