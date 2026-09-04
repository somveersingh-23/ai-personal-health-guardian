package com.healthguardian.member3.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.healthguardian.member3.data.GuardianAlert
import com.healthguardian.member3.data.LoadState

@Composable
fun AlertsScreen(state: LoadState<List<GuardianAlert>>, retry: () -> Unit) {
    when (state) {
        LoadState.Idle, LoadState.Loading -> CircularProgressIndicator(Modifier.padding(24.dp))
        is LoadState.Offline -> StatusPanel("You're offline", if (state.cached) "Showing saved alerts." else state.message, retry)
        is LoadState.Error -> StatusPanel("Alerts unavailable", state.message, retry)
        is LoadState.Ready -> LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            item { Text("Alerts and history", style = MaterialTheme.typography.headlineSmall) }
            if (state.value.isEmpty()) item { Text("No active alerts.") }
            items(state.value, key = { it.id }) { alert -> AlertCard(alert) }
        }
    }
}

@Composable
private fun AlertCard(alert: GuardianAlert) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = if (alert.priority.lowercase() in setOf("critical", "emergency")) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.surfaceVariant)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(alert.title, style = MaterialTheme.typography.titleMedium)
            Text(alert.message)
            Text("${alert.priority.uppercase()} • ${alert.status}", style = MaterialTheme.typography.labelMedium)
        }
    }
}
