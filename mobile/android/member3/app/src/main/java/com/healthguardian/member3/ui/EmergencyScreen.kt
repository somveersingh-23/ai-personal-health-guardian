package com.healthguardian.member3.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.healthguardian.member3.data.*

@Composable
fun EmergencyScreen(caregivers: LoadState<List<Caregiver>>, emergency: LoadState<EmergencyWorkflow>, start: (String) -> Unit, retry: () -> Unit) {
    var reason by rememberSaveable { mutableStateOf("") }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { Text("Emergency and caregivers", style = MaterialTheme.typography.headlineSmall) }
        item { Text("The app never calls emergency services automatically. You must review and confirm every escalation.") }
        item { OutlinedTextField(reason, { reason = it }, Modifier.fillMaxWidth(), label = { Text("What is happening?") }) }
        item { Button(onClick = { start(reason) }, enabled = reason.isNotBlank() && emergency !is LoadState.Loading, colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)) { Text("Start emergency workflow") } }
        when (emergency) {
            is LoadState.Ready -> item { StatusPanel("Workflow ${emergency.value.status}", emergency.value.nextAction) }
            is LoadState.Offline -> item { StatusPanel("Emergency service unavailable", "Call your local emergency number directly if immediate help is needed.", retry) }
            is LoadState.Error -> item { StatusPanel("Unable to start workflow", emergency.message, retry) }
            LoadState.Loading -> item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
            LoadState.Idle -> Unit
        }
        item { HorizontalDivider(); Text("Approved caregivers", style = MaterialTheme.typography.titleLarge) }
        when (caregivers) {
            is LoadState.Ready -> if (caregivers.value.isEmpty()) item { Text("No caregiver has been approved.") } else items(caregivers.value, key = { it.id }) { Text("${it.name} • ${it.status}") }
            is LoadState.Offline -> item { StatusPanel("Caregivers unavailable", caregivers.message, retry) }
            is LoadState.Error -> item { StatusPanel("Caregivers unavailable", caregivers.message, retry) }
            LoadState.Loading -> item { CircularProgressIndicator() }
            LoadState.Idle -> Unit
        }
    }
}
