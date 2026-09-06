package com.healthguardian.app.core.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val LightColorScheme = lightColorScheme(
    primary = AppColors.PrimaryBlue,
    onPrimary = Color.White,
    secondary = AppColors.TealPrimary,
    tertiary = AppColors.SecondaryGreen,
    background = AppColors.BackgroundLight,
    onBackground = AppColors.TextPrimaryLight,
    surface = AppColors.SurfaceLight,
    onSurface = AppColors.TextPrimaryLight,
    surfaceVariant = AppColors.SurfaceVariantLight,
    onSurfaceVariant = AppColors.TextSecondaryLight,
    outline = AppColors.DividerLight,
    error = AppColors.ErrorColor,
    onError = Color.White
)

private val DarkColorScheme = darkColorScheme(
    primary = AppColors.PrimaryBlueLight,
    onPrimary = AppColors.PrimaryBlue,
    secondary = AppColors.TealPrimary,
    tertiary = AppColors.SecondaryGreen,
    background = AppColors.BackgroundDark,
    onBackground = AppColors.TextPrimaryDark,
    surface = AppColors.SurfaceDark,
    onSurface = AppColors.TextPrimaryDark,
    surfaceVariant = AppColors.SurfaceVariantDark,
    onSurfaceVariant = AppColors.TextSecondaryDark,
    outline = AppColors.DividerDark,
    error = AppColors.ErrorColor,
    onError = Color.White
)

@Composable
fun HealthGuardianTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.background.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = AppTypography,
        content = content
    )
}
