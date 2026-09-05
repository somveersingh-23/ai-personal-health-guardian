package com.healthguardian.app.presentation.ui.settings

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.healthguardian.app.core.ui.theme.Spacing

@Composable
fun SettingsScreen() {
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.lg)
    ) {
        item {
            Text(
                text = "Settings",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold
            )
        }

        item {
            SettingsSection(title = "Account") {
                SettingsItem(icon = Icons.Default.Person, label = "Edit Profile")
                SettingsItem(icon = Icons.Default.Lock, label = "Change Password")
            }
        }

        item {
            SettingsSection(title = "Preferences") {
                SettingsItem(icon = Icons.Default.Notifications, label = "Notifications")
                SettingsItem(icon = Icons.Default.Palette, label = "Appearance")
            }
        }

        item {
            SettingsSection(title = "About") {
                SettingsItem(icon = Icons.Default.Info, label = "App Version")
                SettingsItem(icon = Icons.Default.Description, label = "Privacy Policy")
            }
        }

        item {
            Spacer(modifier = Modifier.height(Spacing.xxl))
            Button(
                onClick = { },
                modifier = Modifier.fillMaxWidth().height(48.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
            ) {
                Text(text = "Logout", style = MaterialTheme.typography.labelLarge)
            }
        }
    }
}

@Composable
fun SettingsSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
        Text(
            text = title,
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.primary
        )
        content()
    }
}

@Composable
fun SettingsItem(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String) {
    Row(
        modifier = Modifier.fillMaxWidth().height(56.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.md),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                text = label,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
        }
        Icon(
            imageVector = Icons.Default.ChevronRight,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}