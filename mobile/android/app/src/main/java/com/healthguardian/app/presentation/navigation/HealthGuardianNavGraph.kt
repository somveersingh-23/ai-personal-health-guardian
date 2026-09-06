package com.healthguardian.app.presentation.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.healthguardian.app.presentation.ui.ai.AIChatScreen
import com.healthguardian.app.presentation.ui.dashboard.DashboardScreen
import com.healthguardian.app.presentation.ui.insights.InsightsScreen
import com.healthguardian.app.presentation.ui.onboarding.OnboardingScreen
import com.healthguardian.app.presentation.ui.records.HealthRecordsScreen
import com.healthguardian.app.presentation.ui.settings.SettingsScreen
import com.healthguardian.app.presentation.ui.splash.SplashScreen

@Composable
fun HealthGuardianNavGraph(
    navController: NavHostController,
    startDestination: String = "splash"
) {
    NavHost(
        navController = navController,
        startDestination = startDestination
    ) {

        // ---------------------------------------------------------
        // Splash
        // ---------------------------------------------------------
        composable(route = "splash") {
            SplashScreen(
                onNavigateToOnboarding = {
                    navController.navigate("onboarding") {
                        popUpTo("splash") {
                            inclusive = true
                        }
                    }
                },
                onNavigateToDashboard = {
                    navController.navigate("main") {
                        popUpTo("splash") {
                            inclusive = true
                        }
                    }
                }
            )
        }

        // ---------------------------------------------------------
        // Onboarding
        // ---------------------------------------------------------
        composable(route = "onboarding") {
            OnboardingScreen(
                onComplete = {
                    navController.navigate("main") {
                        popUpTo("onboarding") {
                            inclusive = true
                        }
                    }
                }
            )
        }

        // ---------------------------------------------------------
        // Main Application
        // ---------------------------------------------------------
        composable(route = "main") {
            MainAppScreen()
        }

        // ---------------------------------------------------------
        // Dashboard
        // ---------------------------------------------------------
        composable(route = "dashboard") {
            DashboardScreen()
        }

        // ---------------------------------------------------------
        // AI Guardian
        // ---------------------------------------------------------
        composable(route = "ai_chat") {
            AIChatScreen()
        }

        // ---------------------------------------------------------
        // Health Records
        // ---------------------------------------------------------
        composable(route = "health_records") {
            HealthRecordsScreen()
        }

        // ---------------------------------------------------------
        // Insights
        // ---------------------------------------------------------
        composable(route = "insights") {
            InsightsScreen()
        }

        // ---------------------------------------------------------
        // Settings
        // ---------------------------------------------------------
        composable(route = "settings") {
            SettingsScreen(
                onBackClick = {
                    navController.navigate("dashboard") {
                        popUpTo("settings") {
                            inclusive = true
                        }
                    }
                }
            )
        }
    }
}