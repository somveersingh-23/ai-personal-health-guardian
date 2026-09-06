package com.healthguardian.app.presentation.navigation

sealed class NavRoute(val route: String) {
    data object Splash : NavRoute("splash")
    data object Onboarding : NavRoute("onboarding")
    data object Login : NavRoute("login")
    data object Register : NavRoute("register")
    data object Main : NavRoute("main")
    data object Dashboard : NavRoute("dashboard")
    data object HealthProfile : NavRoute("profile")
    data object HealthRecords : NavRoute("health_records")
    data object AIChat : NavRoute("ai_chat")
    data object Insights : NavRoute("insights")
    data object Settings : NavRoute("settings")

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
    data object Dashboard : BottomNavItem(NavRoute.Dashboard, "🏠", "Home")
    data object AIChat : BottomNavItem(NavRoute.AIChat, "🤖", "AI")
    data object HealthRecords : BottomNavItem(NavRoute.HealthRecords, "📋", "Health")
    data object Insights : BottomNavItem(NavRoute.Insights, "📊", "Insights")
    data object Settings : BottomNavItem(NavRoute.Settings, "⚙️", "Profile")

    companion object {
        val items = listOf(Dashboard, AIChat, HealthRecords, Insights, Settings)
    }
}
