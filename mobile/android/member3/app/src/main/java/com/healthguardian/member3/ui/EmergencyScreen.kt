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
fun EmergencyScreen(
    caregivers: LoadState<List<Caregiver>>,
    emergency: LoadState<EmergencyWorkflow>,
    start: (String) -> Unit,
    inviteCaregiver: ((String, String) -> Unit)? = null,
    retry: () -> Unit,
) {
    var reason by rememberSaveable { mutableStateOf("") }
    var caregiverRef by rememberSaveable { mutableStateOf("") }
    var relationship by rememberSaveable { mutableStateOf("") }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text("Emergency and caregivers", style = MaterialTheme.typography.headlineSmall)
        }
        item {
            Text("The app never calls emergency services automatically. You must review and confirm every escalation.")
        }
        item {
            OutlinedTextField(
                value = reason,
                onValueChange = { reason = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("What is happening?") },
            )
        }
        item {
            Button(
                onClick = { start(reason) },
                enabled = reason.isNotBlank() && emergency !is LoadState.Loading,
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Start emergency workflow")
            }
        }
        when (emergency) {
            is LoadState.Ready -> item {
                StatusPanel("Workflow ${emergency.value.status}", emergency.value.nextAction)
            }
            is LoadState.Offline -> item {
                StatusPanel(
                    "Emergency service unavailable",
                    "Call your local emergency number directly if immediate help is needed.",
                    retry,
                )
            }
            is LoadState.Error -> item {
                StatusPanel("Unable to start workflow", emergency.message, retry)
            }
            LoadState.Loading -> item {
                LinearProgressIndicator(Modifier.fillMaxWidth())
            }
            LoadState.Idle -> Unit
        }

        item {
            HorizontalDivider()
            Text("Approved caregivers & consent", style = MaterialTheme.typography.titleLarge)
            Text(
                "Caregivers receive critical notifications only after mutual two-party consent.",
                style = MaterialTheme.typography.bodySmall,
            )
        }

        if (inviteCaregiver != null) {
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("Invite Caregiver", style = MaterialTheme.typography.titleSmall)
                        OutlinedTextField(
                            value = caregiverRef,
                            onValueChange = { caregiverRef = it },
                            label = { Text("Caregiver User ID") },
                            modifier = Modifier.fillMaxWidth(),
                        )
                        OutlinedTextField(
                            value = relationship,
                            onValueChange = { relationship = it },
                            label = { Text("Relationship (e.g. Spouse, Parent)") },
                            modifier = Modifier.fillMaxWidth(),
                        )
                        Button(
                            onClick = {
                                inviteCaregiver(caregiverRef, relationship)
                                caregiverRef = ""
                                relationship = ""
                            },
                            enabled = caregiverRef.isNotBlank() && relationship.isNotBlank(),
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Text("Send Invitation")
                        }
                    }
                }
            }
        }

        when (caregivers) {
            is LoadState.Ready -> {
                if (caregivers.value.isEmpty()) {
                    item { Text("No caregiver has been approved.") }
                } else {
                    items(caregivers.value, key = { it.id }) { caregiver ->
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Text(caregiver.name, style = MaterialTheme.typography.titleMedium)
                                Text("Status: ${caregiver.status.uppercase()}", style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                }
            }
            is LoadState.Offline -> item {
                StatusPanel("Caregivers unavailable", caregivers.message, retry)
            }
            is LoadState.Error -> item {
                StatusPanel("Caregivers unavailable", caregivers.message, retry)
            }
            LoadState.Loading -> item {
                CircularProgressIndicator()
            }
            LoadState.Idle -> Unit
        }
    }
}
