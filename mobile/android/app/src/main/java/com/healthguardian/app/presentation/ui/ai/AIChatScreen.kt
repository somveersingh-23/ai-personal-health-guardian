package com.healthguardian.app.presentation.ui.ai

import androidx.activity.compose.LocalOnBackPressedDispatcherOwner
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.healthguardian.app.core.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AIChatScreen() {

    var messageText by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    val backDispatcher = LocalOnBackPressedDispatcherOwner.current?.onBackPressedDispatcher

    val messages = remember {
        mutableStateListOf(
            AIMessage(
                id = "1",
                role = "ASSISTANT",
                content = "Hello! I'm your AI Health Guardian. How can I help you today?",
                requiresUrgentAttention = false
            )
        )
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .imePadding()
    ) {

        // Top App Bar
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .padding(
                    start = Spacing.md,
                    end = Spacing.md,
                    top = Spacing.sm
                ),
            shape = RoundedCornerShape(CornerRadius.lg),
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 2.dp,
            shadowElevation = 1.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(
                        horizontal = Spacing.sm,
                        vertical = Spacing.sm
                    ),
                verticalAlignment = Alignment.CenterVertically
            ) {

                IconButton(
                    onClick = {
                        backDispatcher?.onBackPressed()
                    },
                    modifier = Modifier.size(44.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.ArrowBack,
                        contentDescription = "Go back",
                        tint = MaterialTheme.colorScheme.onSurface
                    )
                }

                Spacer(modifier = Modifier.width(Spacing.sm))

                Box(
                    modifier = Modifier
                        .size(42.dp)
                        .background(
                            color = TealPrimary,
                            shape = CircleShape
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.SmartToy,
                        contentDescription = "AI Health Guardian",
                        tint = MaterialTheme.colorScheme.onPrimary,
                        modifier = Modifier.size(23.dp)
                    )
                }

                Spacer(modifier = Modifier.width(Spacing.sm))

                Column(
                    modifier = Modifier.weight(1f)
                ) {
                    Text(
                        text = "AI Health Guardian",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface
                    )

                    Text(
                        text = "Educational support • Not medical diagnosis",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(Spacing.sm))

        // Chat messages
        LazyColumn(
            state = listState,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = Spacing.md),
            contentPadding = PaddingValues(
                top = Spacing.sm,
                bottom = Spacing.md
            ),
            verticalArrangement = Arrangement.spacedBy(Spacing.md)
        ) {
            items(
                messages,
                key = { it.id }
            ) { message ->

                if (message.role == "USER") {
                    UserMessageBubble(message.content)
                } else {
                    AiMessageBubble(message)
                }
            }
        }

        // Message composer
        MessageComposer(
            text = messageText,
            onTextChange = {
                messageText = it
            },
            onSend = {
                if (messageText.isNotBlank()) {

                    messages.add(
                        AIMessage(
                            id = System.currentTimeMillis().toString(),
                            role = "USER",
                            content = messageText.trim(),
                            requiresUrgentAttention = false
                        )
                    )

                    messageText = ""
                }
            },
            modifier = Modifier
                .fillMaxWidth()
                .padding(
                    start = Spacing.md,
                    end = Spacing.md,
                    bottom = 88.dp
                )
        )
    }
}

@Composable
fun UserMessageBubble(content: String) {

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.End
    ) {

        Surface(
            modifier = Modifier.widthIn(max = 310.dp),
            shape = RoundedCornerShape(
                topStart = CornerRadius.lg,
                topEnd = CornerRadius.lg,
                bottomStart = CornerRadius.lg,
                bottomEnd = 6.dp
            ),
            color = UserMessageBubble
        ) {
            Text(
                text = content,
                style = MaterialTheme.typography.bodyLarge,
                color = UserMessageText,
                modifier = Modifier.padding(
                    horizontal = Spacing.md,
                    vertical = Spacing.sm
                )
            )
        }
    }
}

@Composable
fun AiMessageBubble(message: AIMessage) {

    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm)
    ) {

        if (message.requiresUrgentAttention) {

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(CornerRadius.md),
                colors = CardDefaults.cardColors(
                    containerColor = CriticalHealthWarning.copy(alpha = 0.10f)
                )
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(Spacing.md),
                    horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                    verticalAlignment = Alignment.Top
                ) {

                    Icon(
                        imageVector = Icons.Default.Warning,
                        contentDescription = "Warning",
                        tint = CriticalHealthWarning
                    )

                    Text(
                        text = "Consider contacting a healthcare professional.",
                        style = MaterialTheme.typography.bodySmall,
                        color = CriticalHealthWarning,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            verticalAlignment = Alignment.Top
        ) {

            // AI avatar
            Box(
                modifier = Modifier
                    .size(38.dp)
                    .background(
                        color = TealPrimary,
                        shape = CircleShape
                    ),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.SmartToy,
                    contentDescription = "AI",
                    tint = MaterialTheme.colorScheme.onPrimary,
                    modifier = Modifier.size(21.dp)
                )
            }

            // AI message
            Surface(
                modifier = Modifier.widthIn(max = 310.dp),
                shape = RoundedCornerShape(
                    topStart = 6.dp,
                    topEnd = CornerRadius.lg,
                    bottomStart = CornerRadius.lg,
                    bottomEnd = CornerRadius.lg
                ),
                color = MaterialTheme.colorScheme.surfaceVariant,
                tonalElevation = 1.dp
            ) {
                Text(
                    text = message.content,
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(
                        horizontal = Spacing.md,
                        vertical = Spacing.sm
                    )
                )
            }
        }
    }
}

@Composable
fun MessageComposer(
    text: String,
    onTextChange: (String) -> Unit,
    onSend: () -> Unit,
    modifier: Modifier = Modifier
) {

    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(CornerRadius.xl),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 4.dp,
        shadowElevation = 3.dp
    ) {

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(
                    start = Spacing.sm,
                    end = Spacing.xs,
                    top = Spacing.xs,
                    bottom = Spacing.xs
                ),
            verticalAlignment = Alignment.Bottom
        ) {

            OutlinedTextField(
                value = text,
                onValueChange = onTextChange,
                placeholder = {
                    Text(
                        text = "Ask about your health..."
                    )
                },
                modifier = Modifier
                    .weight(1f)
                    .padding(end = Spacing.xs),
                shape = RoundedCornerShape(CornerRadius.lg),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = MaterialTheme.colorScheme.surface,
                    unfocusedContainerColor = MaterialTheme.colorScheme.surface,
                    focusedBorderColor = MaterialTheme.colorScheme.primary,
                    unfocusedBorderColor = MaterialTheme.colorScheme.outline.copy(
                        alpha = 0.5f
                    )
                ),
                maxLines = 4,
                singleLine = false
            )

            Spacer(modifier = Modifier.width(Spacing.xs))

            FilledIconButton(
                onClick = onSend,
                enabled = text.isNotBlank(),
                modifier = Modifier.size(46.dp),
                shape = CircleShape,
                colors = IconButtonDefaults.filledIconButtonColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    disabledContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                    contentColor = MaterialTheme.colorScheme.onPrimary,
                    disabledContentColor = MaterialTheme.colorScheme.onSurfaceVariant
                )
            ) {
                Icon(
                    imageVector = Icons.Default.Send,
                    contentDescription = "Send message",
                    modifier = Modifier.size(20.dp)
                )
            }
        }
    }
}

data class AIMessage(
    val id: String,
    val role: String,
    val content: String,
    val requiresUrgentAttention: Boolean
)