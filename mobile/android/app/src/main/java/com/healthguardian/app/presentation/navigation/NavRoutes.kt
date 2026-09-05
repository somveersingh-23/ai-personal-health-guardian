package com.healthguardian.app.presentation.navigation

sealed class NavRoute(val route: String) {
    object Splash : NavRoute("splash")
    object Onboarding : NavRoute("onboarding")
    object Login : NavRoute("login")
    object Register : NavRoute("register")
    object Main : NavRoute("main")
    object Dashboard : NavRoute("dashboard")
    object HealthProfile : NavRoute("profile")
    object HealthRecords : NavRoute("health_records")
    object AIChat : NavRoute("ai_chat")
    object Insights : NavRoute("insights")
    object Settings : NavRoute("settings")

    companion object {
        val bottomNavRoutes = listOf(
            Dashboard, AIChat, HealthRecords, Insights, Settings
        )
    }
}

sealed class BottomNavItem(
    val route: NavRoute,
    val icon: String,
    val label: String
) {
    object Dashboard : BottomNavItem(NavRoute.Dashboard, "🏠", "Home")
    object AIChat : BottomNavItem(NavRoute.AIChat, "🤖", "AI")
    object HealthRecords : BottomNavItem(NavRoute.HealthRecords, "📋", "Health")
    object Insights : BottomNavItem(NavRoute.Insights, "📊", "Insights")
    object Settings : BottomNavItem(NavRoute.Settings, "⚙️", "Profile")

    companion object {
        val items = listOf(Dashboard, AIChat, HealthRecords, Insights, Settings)
    }
}