package com.healthguardian.app.presentation.ui.settings

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.LightMode
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.NotificationsOff
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.PrivacyTip
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.healthguardian.app.core.ui.theme.Spacing

private const val PREFS_NAME = "health_guardian_settings"
private const val KEY_NOTIFICATIONS_ENABLED = "notifications_enabled"

private const val APP_VERSION = "1.0.0"

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onBackClick: () -> Unit = {}
) {
    val context = LocalContext.current

    val preferences = remember {
        context.getSharedPreferences(
            PREFS_NAME,
            Context.MODE_PRIVATE
        )
    }

    var notificationsEnabled by remember {
        mutableStateOf(
            preferences.getBoolean(
                KEY_NOTIFICATIONS_ENABLED,
                true
            )
        )
    }

    var showAppearanceDialog by remember {
        mutableStateOf(false)
    }

    var showPrivacyDialog by remember {
        mutableStateOf(false)
    }

    var showVersionDialog by remember {
        mutableStateOf(false)
    }

    var appearanceMode by remember {
        mutableStateOf("System")
    }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background
    ) { innerPadding ->

        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .windowInsetsPadding(WindowInsets.safeDrawing)
                .padding(horizontal = Spacing.md),
            verticalArrangement = Arrangement.spacedBy(Spacing.md)
        ) {

            // ---------------------------------------------------------
            // TOP BAR
            // ---------------------------------------------------------

            item {
                Spacer(modifier = Modifier.height(Spacing.xs))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {

                    IconButton(
                        onClick = onBackClick,
                        modifier = Modifier
                            .size(44.dp)
                            .clip(CircleShape)
                    ) {
                        Icon(
                            imageVector = Icons.Default.ArrowBack,
                            contentDescription = "Back to Dashboard",
                            tint = MaterialTheme.colorScheme.onSurface
                        )
                    }

                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .padding(start = Spacing.sm)
                    ) {
                        Text(
                            text = "Settings",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onBackground
                        )

                        Text(
                            text = "Customize your Health Guardian experience",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    Surface(
                        modifier = Modifier.size(42.dp),
                        shape = CircleShape,
                        color = MaterialTheme.colorScheme.primaryContainer
                    ) {
                        Box(
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Settings,
                                contentDescription = "Settings",
                                tint = MaterialTheme.colorScheme.primary
                            )
                        }
                    }
                }
            }

            // ---------------------------------------------------------
            // PREFERENCES
            // ---------------------------------------------------------

            item {
                SettingsSection(
                    title = "Preferences",
                    subtitle = "Control how Health Guardian behaves"
                ) {
                    SettingsCard {

                        NotificationSettingItem(
                            enabled = notificationsEnabled,
                            onEnabledChange = { enabled ->

                                notificationsEnabled = enabled

                                preferences.edit()
                                    .putBoolean(
                                        KEY_NOTIFICATIONS_ENABLED,
                                        enabled
                                    )
                                    .apply()
                            }
                        )

                        SettingsDivider()

                        SettingsItem(
                            icon = Icons.Default.Palette,
                            label = "Appearance",
                            description = appearanceMode,
                            onClick = {
                                showAppearanceDialog = true
                            }
                        )
                    }
                }
            }

            // ---------------------------------------------------------
            // PRIVACY
            // ---------------------------------------------------------

            item {
                SettingsSection(
                    title = "Privacy & Data",
                    subtitle = "Understand how your health information is handled"
                ) {
                    SettingsCard {

                        SettingsItem(
                            icon = Icons.Default.PrivacyTip,
                            label = "Privacy Policy",
                            description = "How your health data is handled",
                            onClick = {
                                showPrivacyDialog = true
                            }
                        )
                    }
                }
            }

            // ---------------------------------------------------------
            // ABOUT
            // ---------------------------------------------------------

            item {
                SettingsSection(
                    title = "About",
                    subtitle = "Information about this application"
                ) {
                    SettingsCard {

                        SettingsItem(
                            icon = Icons.Default.Info,
                            label = "App Version",
                            description = "Version $APP_VERSION",
                            onClick = {
                                showVersionDialog = true
                            }
                        )

                        SettingsDivider()

                        SettingsItem(
                            icon = Icons.Default.Description,
                            label = "About Health Guardian",
                            description = "Personal health intelligence",
                            onClick = {
                                showVersionDialog = true
                            }
                        )
                    }
                }
            }

            // ---------------------------------------------------------
            // PRIVACY NOTE
            // ---------------------------------------------------------

            item {
                PrivacyNoticeCard()
            }

            // ---------------------------------------------------------
            // FOOTER
            // ---------------------------------------------------------

            item {
                Spacer(modifier = Modifier.height(Spacing.sm))

                Text(
                    text = "AI Personal Health Guardian",
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.bodySmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Text(
                    text = "Privacy-first personal health intelligence",
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 4.dp),
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(
                    modifier = Modifier.height(
                        Spacing.lg
                    )
                )
            }
        }
    }

    // -------------------------------------------------------------
    // APPEARANCE DIALOG
    // -------------------------------------------------------------

    if (showAppearanceDialog) {
        AppearanceDialog(
            currentMode = appearanceMode,
            onModeSelected = { mode ->
                appearanceMode = mode
                showAppearanceDialog = false
            },
            onDismiss = {
                showAppearanceDialog = false
            }
        )
    }

    // -------------------------------------------------------------
    // PRIVACY POLICY DIALOG
    // -------------------------------------------------------------

    if (showPrivacyDialog) {
        PrivacyPolicyDialog(
            onDismiss = {
                showPrivacyDialog = false
            }
        )
    }

    // -------------------------------------------------------------
    // APP VERSION DIALOG
    // -------------------------------------------------------------

    if (showVersionDialog) {
        AppVersionDialog(
            onDismiss = {
                showVersionDialog = false
            }
        )
    }
}


// =================================================================
// SETTINGS SECTION
// =================================================================

@Composable
private fun SettingsSection(
    title: String,
    subtitle: String,
    content: @Composable ColumnScope.() -> Unit
) {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm)
    ) {

        Text(
            text = title,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )

        Text(
            text = subtitle,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        content()
    }
}


// =================================================================
// SETTINGS CARD
// =================================================================

@Composable
private fun SettingsCard(
    content: @Composable ColumnScope.() -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(
            defaultElevation = 1.dp
        )
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            content = content
        )
    }
}


// =================================================================
// NOTIFICATION SETTING
// =================================================================

@Composable
private fun NotificationSettingItem(
    enabled: Boolean,
    onEnabledChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable {
                onEnabledChange(!enabled)
            }
            .padding(
                horizontal = Spacing.md,
                vertical = 14.dp
            ),
        verticalAlignment = Alignment.CenterVertically
    ) {

        Surface(
            modifier = Modifier.size(44.dp),
            shape = RoundedCornerShape(14.dp),
            color = if (enabled) {
                MaterialTheme.colorScheme.primaryContainer
            } else {
                MaterialTheme.colorScheme.surfaceVariant
            }
        ) {
            Box(
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = if (enabled) {
                        Icons.Default.Notifications
                    } else {
                        Icons.Default.NotificationsOff
                    },
                    contentDescription = "Notifications",
                    tint = if (enabled) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant
                    }
                )
            }
        }

        Column(
            modifier = Modifier
                .weight(1f)
                .padding(start = Spacing.md)
        ) {

            Text(
                text = "Notifications",
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface
            )

            Text(
                text = if (enabled) {
                    "Health alerts and reminders are enabled"
                } else {
                    "Health alerts and reminders are disabled"
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        Switch(
            checked = enabled,
            onCheckedChange = onEnabledChange
        )
    }
}


// =================================================================
// NORMAL SETTINGS ITEM
// =================================================================

@Composable
private fun SettingsItem(
    icon: ImageVector,
    label: String,
    description: String,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(
                horizontal = Spacing.md,
                vertical = 14.dp
            ),
        verticalAlignment = Alignment.CenterVertically
    ) {

        Surface(
            modifier = Modifier.size(44.dp),
            shape = RoundedCornerShape(14.dp),
            color = MaterialTheme.colorScheme.secondaryContainer
        ) {
            Box(
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = label,
                    tint = MaterialTheme.colorScheme.secondary
                )
            }
        }

        Column(
            modifier = Modifier
                .weight(1f)
                .padding(start = Spacing.md)
        ) {

            Text(
                text = label,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface
            )

            Text(
                text = description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        Icon(
            imageVector = Icons.Default.ChevronRight,
            contentDescription = "Open $label",
            tint = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}


// =================================================================
// DIVIDER
// =================================================================

@Composable
private fun SettingsDivider() {
    Divider(
        modifier = Modifier.padding(horizontal = Spacing.md),
        color = MaterialTheme.colorScheme.outlineVariant
    )
}


// =================================================================
// APPEARANCE DIALOG
// =================================================================

@Composable
private fun AppearanceDialog(
    currentMode: String,
    onModeSelected: (String) -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = {
            Icon(
                imageVector = Icons.Default.Palette,
                contentDescription = null
            )
        },
        title = {
            Text(
                text = "Appearance",
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column {

                AppearanceOption(
                    icon = Icons.Default.Settings,
                    title = "System",
                    selected = currentMode == "System",
                    onClick = {
                        onModeSelected("System")
                    }
                )

                AppearanceOption(
                    icon = Icons.Default.LightMode,
                    title = "Light",
                    selected = currentMode == "Light",
                    onClick = {
                        onModeSelected("Light")
                    }
                )

                AppearanceOption(
                    icon = Icons.Default.DarkMode,
                    title = "Dark",
                    selected = currentMode == "Dark",
                    onClick = {
                        onModeSelected("Dark")
                    }
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = onDismiss
            ) {
                Text("Close")
            }
        }
    )
}


// =================================================================
// APPEARANCE OPTION
// =================================================================

@Composable
private fun AppearanceOption(
    icon: ImageVector,
    title: String,
    selected: Boolean,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {

        Icon(
            imageVector = icon,
            contentDescription = null,
            modifier = Modifier.size(22.dp),
            tint = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Text(
            text = title,
            modifier = Modifier
                .weight(1f)
                .padding(start = 12.dp),
            style = MaterialTheme.typography.bodyLarge
        )

        RadioButton(
            selected = selected,
            onClick = onClick
        )
    }
}


// =================================================================
// PRIVACY POLICY
// =================================================================

@Composable
private fun PrivacyPolicyDialog(
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = {
            Icon(
                imageVector = Icons.Default.PrivacyTip,
                contentDescription = null
            )
        },
        title = {
            Text(
                text = "Privacy Policy",
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            LazyColumn(
                modifier = Modifier.height(420.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {

                item {
                    PolicyHeading("Our Privacy Approach")
                }

                item {
                    PolicyText(
                        "AI Personal Health Guardian is designed as a " +
                                "privacy-first personal health intelligence " +
                                "application. The application is intended to " +
                                "help users understand their health information " +
                                "and identify meaningful changes over time."
                    )
                }

                item {
                    PolicyHeading("Health Information")
                }

                item {
                    PolicyText(
                        "Health information may include profile information, " +
                                "health records, measurements, trends, symptoms, " +
                                "and other information entered or generated through " +
                                "supported features."
                    )
                }

                item {
                    PolicyHeading("Use of Data")
                }

                item {
                    PolicyText(
                        "Health information is used to provide application " +
                                "features such as health records, personal trends, " +
                                "digital health insights, and AI-assisted explanations."
                    )
                }

                item {
                    PolicyHeading("Notifications")
                }

                item {
                    PolicyText(
                        "Notifications are optional. You can enable or disable " +
                                "application notifications from Settings. Future " +
                                "health alerts will respect this preference."
                    )
                }

                item {
                    PolicyHeading("AI Features")
                }

                item {
                    PolicyText(
                        "AI-generated information is intended to assist with " +
                                "understanding health information. It should not be " +
                                "treated as a medical diagnosis or a replacement for " +
                                "professional medical advice."
                    )
                }

                item {
                    PolicyHeading("Data Security")
                }

                item {
                    PolicyText(
                        "The application should use secure communication and " +
                                "appropriate storage protections when deployed in " +
                                "production. Development configurations may use local " +
                                "network endpoints."
                    )
                }

                item {
                    PolicyHeading("Your Control")
                }

                item {
                    PolicyText(
                        "You should be able to control optional application " +
                                "features and notification preferences. Data access " +
                                "and deletion capabilities depend on the backend " +
                                "implementation of the project."
                    )
                }

                item {
                    PolicyHeading("Important Health Disclaimer")
                }

                item {
                    PolicyText(
                        "This application is a personal health intelligence " +
                                "and educational support system. It is not intended " +
                                "to diagnose, treat, cure, or prevent disease. For " +
                                "urgent or emergency symptoms, contact appropriate " +
                                "local emergency or medical services."
                    )
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = onDismiss
            ) {
                Text("I Understand")
            }
        }
    )
}


// =================================================================
// POLICY HEADING
// =================================================================

@Composable
private fun PolicyHeading(
    text: String
) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleSmall,
        fontWeight = FontWeight.Bold,
        color = MaterialTheme.colorScheme.primary
    )
}


// =================================================================
// POLICY TEXT
// =================================================================

@Composable
private fun PolicyText(
    text: String
) {
    Text(
        text = text,
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )
}


// =================================================================
// VERSION DIALOG
// =================================================================

@Composable
private fun AppVersionDialog(
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = {
            Surface(
                modifier = Modifier.size(52.dp),
                shape = CircleShape,
                color = MaterialTheme.colorScheme.primaryContainer
            ) {
                Box(
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Info,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
            }
        },
        title = {
            Text(
                text = "AI Personal Health Guardian",
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )
        },
        text = {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {

                Text(
                    text = "Version $APP_VERSION",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )

                Text(
                    text = "Privacy-first personal health intelligence",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center
                )

                Text(
                    text = "Designed to help users understand " +
                            "personal health information, trends, " +
                            "and changes over time.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = onDismiss
            ) {
                Text("Close")
            }
        }
    )
}


// =================================================================
// PRIVACY NOTICE CARD
// =================================================================

@Composable
private fun PrivacyNoticeCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        )
    ) {

        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.Top
        ) {

            Icon(
                imageVector = Icons.Default.PrivacyTip,
                contentDescription = null,
                modifier = Modifier.size(24.dp),
                tint = MaterialTheme.colorScheme.primary
            )

            Column(
                modifier = Modifier.padding(start = 12.dp)
            ) {

                Text(
                    text = "Your health data matters",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )

                Spacer(
                    modifier = Modifier.height(4.dp)
                )

                Text(
                    text = "Health Guardian is designed with a " +
                            "privacy-first approach. Review the Privacy " +
                            "Policy to understand how health information " +
                            "is intended to be handled.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
        }
    }
}