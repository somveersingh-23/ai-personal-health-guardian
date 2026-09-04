package com.healthguardian.member3.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.healthguardian.member3.data.AssistantMessage
import com.healthguardian.member3.data.LoadState

@Composable
fun AssistantScreen(messages: List<AssistantMessage>, loadState: LoadState<Unit>, send: (String) -> Unit) {
    var question by rememberSaveable { mutableStateOf("") }
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Ask about your health changes", style = MaterialTheme.typography.headlineSmall)
        Text("This assistant provides information, not a diagnosis. For urgent symptoms, contact local emergency services.", style = MaterialTheme.typography.bodySmall)
        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            if (messages.isEmpty()) item { Text("Your conversation will appear here.") }
            items(messages, key = { it.id }) { message ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = if (message.fromUser) Arrangement.End else Arrangement.Start) {
                    Surface(color = if (message.fromUser) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant, shape = MaterialTheme.shapes.medium) {
                        Text(message.text, Modifier.padding(12.dp).widthIn(max = 300.dp))
                    }
                }
            }
            if (loadState is LoadState.Loading) item { LinearProgressIndicator(Modifier.fillMaxWidth().semantics { contentDescription = "Assistant loading" }) }
            if (loadState is LoadState.Offline) item { Text("Offline: ${loadState.message}", color = MaterialTheme.colorScheme.error) }
            if (loadState is LoadState.Error) item { Text(loadState.message, color = MaterialTheme.colorScheme.error) }
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(question, { question = it }, Modifier.weight(1f), label = { Text("Your question") }, enabled = loadState !is LoadState.Loading)
            Button(onClick = { send(question); question = "" }, enabled = question.isNotBlank() && loadState !is LoadState.Loading) { Text("Send") }
        }
    }
}
