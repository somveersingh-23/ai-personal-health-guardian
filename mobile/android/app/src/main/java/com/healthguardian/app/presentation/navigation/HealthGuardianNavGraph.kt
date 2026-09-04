package com.healthguardian.app.presentation.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.healthguardian.app.presentation.ui.splash.SplashScreen
import com.healthguardian.app.presentation.ui.onboarding.OnboardingScreen
import com.healthguardian.app.presentation.ui.auth.LoginScreen
import com.healthguardian.app.presentation.ui.auth.RegisterScreen
import com.healthguardian.app.presentation.ui.dashboard.DashboardScreen
import com.healthguardian.app.presentation.ui.ai.AIChatScreen
import com.healthguardian.app.presentation.ui.records.HealthRecordsScreen
import com.healthguardian.app.presentation.ui.insights.InsightsScreen
import com.healthguardian.app.presentation.ui.settings.SettingsScreen

@Composable
fun HealthGuardianNavGraph(
    navController: NavHostController,
    startDestination: String = "splash"
) {
    NavHost(
        navController = navController,
        startDestination = startDestination
    ) {
        composable(route = "splash") {
            SplashScreen(
                onNavigateToOnboarding = {
                    navController.navigate("onboarding") {
                        popUpTo("splash") { inclusive = true }
                    }
                },
                onNavigateToDashboard = {
                    navController.navigate("main") {
                        popUpTo("splash") { inclusive = true }
                    }
                }
            )
        }

        composable(route = "onboarding") {
            OnboardingScreen(
                onComplete = {
                    navController.navigate("main") {
                        popUpTo("onboarding") { inclusive = true }
                    }
                }
            )
        }

        composable(route = "login") {
            LoginScreen(
                onLoginSuccess = {
                    navController.navigate("main") {
                        popUpTo("login") { inclusive = true }
                    }
                },
                onNavigateToRegister = {
                    navController.navigate("register")
                }
            )
        }

        composable(route = "register") {
            RegisterScreen(
                onRegisterSuccess = {
                    navController.navigate("main") {
                        popUpTo("register") { inclusive = true }
                    }
                },
                onNavigateToLogin = {
                    navController.popBackStack()
                }
            )
        }

        composable(route = "main") {
            MainAppScreen()
        }

        composable(route = "dashboard") {
            DashboardScreen()
        }

        composable(route = "ai_chat") {
            AIChatScreen()
        }

        composable(route = "health_records") {
            HealthRecordsScreen()
        }

        composable(route = "insights") {
            InsightsScreen()
        }

        composable(route = "settings") {
            SettingsScreen()
        }
    }
}