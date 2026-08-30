package com.healthguardian.member3.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.healthguardian.member3.data.Member3Repository

private enum class Destination(val route: String, val label: String, val icon: ImageVector) {
    ASSISTANT("assistant", "Assistant", Icons.Default.Chat),
    INSIGHTS("insights", "Insights", Icons.Default.Insights),
    ALERTS("alerts", "Alerts", Icons.Default.Notifications),
    EMERGENCY("emergency", "Emergency", Icons.Default.HealthAndSafety),
}

@Composable
fun GuardianApp(repository: Member3Repository) {
    val model: GuardianViewModel = viewModel(factory = GuardianViewModel.Factory(repository))
    val state by model.state.collectAsStateWithLifecycle()
    val nav = rememberNavController()
    val current by nav.currentBackStackEntryAsState()
    LaunchedEffect(Unit) { model.refresh() }

    Scaffold(
        topBar = { TopAppBar(title = { Text("AI Health Guardian") }) },
        bottomBar = {
            NavigationBar {
                Destination.entries.forEach { destination ->
                    NavigationBarItem(
                        selected = current?.destination?.route == destination.route,
                        onClick = {
                            nav.navigate(destination.route) {
                                popUpTo(nav.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(destination.icon, contentDescription = destination.label) },
                        label = { Text(destination.label) },
                    )
                }
            }
        },
    ) { padding ->
        NavHost(navController = nav, startDestination = Destination.ASSISTANT.route, modifier = Modifier.padding(padding)) {
            composable(Destination.ASSISTANT.route) { AssistantScreen(state.messages, state.assistantState, model::sendQuestion) }
            composable(Destination.INSIGHTS.route) { InsightsScreen(state.insights, model::refresh) }
            composable(Destination.ALERTS.route) { AlertsScreen(state.alerts, model::refresh) }
            composable(Destination.EMERGENCY.route) { EmergencyScreen(state.caregivers, state.emergency, model::startEmergency, model::refresh) }
        }
    }
}

@Composable
internal fun StatusPanel(title: String, message: String, action: (() -> Unit)? = null) {
    Card(Modifier.fillMaxWidth().padding(16.dp)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(message)
            action?.let { TextButton(onClick = it) { Text("Try again") } }
        }
    }
}
