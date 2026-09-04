package com.healthguardian.member3.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.healthguardian.member3.data.HealthInsight
import com.healthguardian.member3.data.LoadState

@Composable
fun InsightsScreen(state: LoadState<List<HealthInsight>>, retry: () -> Unit) {
    when (state) {
        LoadState.Idle, LoadState.Loading -> Box(Modifier.fillMaxSize()) { CircularProgressIndicator(Modifier.padding(24.dp)) }
        is LoadState.Offline -> StatusPanel("You're offline", if (state.cached) "Showing the last saved insights." else state.message, retry)
        is LoadState.Error -> StatusPanel("Insights unavailable", state.message, retry)
        is LoadState.Ready -> LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            item { Text("Health insights", style = MaterialTheme.typography.headlineSmall) }
            if (state.value.isEmpty()) item { Text("No new insights. Your meaningful changes will appear here.") }
            items(state.value, key = { it.id }) { InsightCard(it) }
        }
    }
}

@Composable
private fun InsightCard(insight: HealthInsight) {
    Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(insight.title, style = MaterialTheme.typography.titleMedium)
        Text(insight.summary)
        Text(insight.status.uppercase(), style = MaterialTheme.typography.labelSmall)
    } }
}
