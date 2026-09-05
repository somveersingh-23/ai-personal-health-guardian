package com.healthguardian.app.presentation.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.healthguardian.app.core.ui.theme.*

@Composable
fun DashboardScreen() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(
                start = Spacing.md,
                end = Spacing.md,
                top = 16.dp, // Safe area for status bar
                bottom = 90.dp // Space for bottom nav
            ),
            verticalArrangement = Arrangement.spacedBy(Spacing.lg)
        ) {
            // TOP BAR
            item {
                DashboardTopBar()
            }

            // GREETING
            item {
                GreetingSection()
            }

            // HEALTH SCORE
            item {
                HealthScoreCard()
            }

            // HEALTH OVERVIEW
            item {
                SectionHeader(
                    title = "Health Overview",
                    action = "View all"
                )
            }

            item {
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.md),
                    contentPadding = PaddingValues(end = Spacing.sm)
                ) {
                    items(4) { index ->
                        HealthMetricCard(
                            icon = when (index) {
                                0 -> Icons.Default.Favorite
                                1 -> Icons.Default.Bedtime
                                2 -> Icons.Default.DirectionsWalk
                                else -> Icons.Default.MonitorWeight
                            },
                            metric = when (index) {
                                0 -> "Heart Rate"
                                1 -> "Sleep"
                                2 -> "Steps"
                                else -> "Weight"
                            },
                            value = when (index) {
                                0 -> "72"
                                1 -> "7.5"
                                2 -> "8,432"
                                else -> "70"
                            },
                            unit = when (index) {
                                0 -> "bpm"
                                1 -> "hrs"
                                2 -> "steps"
                                else -> "kg"
                            }
                        )
                    }
                }
            }

            // AI GUARDIAN
            item {
                AIGuardianCard()
            }

            // QUICK ACTIONS
            item {
                SectionHeader(title = "Quick Actions")
            }

            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(Spacing.sm)
                ) {
                    QuickActionButton(
                        icon = Icons.Default.Add,
                        label = "Add Record",
                        modifier = Modifier.weight(1f)
                    )

                    QuickActionButton(
                        icon = Icons.Default.SmartToy,
                        label = "Ask AI",
                        modifier = Modifier.weight(1f)
                    )

                    QuickActionButton(
                        icon = Icons.Default.Insights,
                        label = "Insights",
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            // RECENT ACTIVITY
            item {
                SectionHeader(
                    title = "Recent Activity",
                    action = "See all"
                )
            }

            items(3) { index ->
                RecentActivityCard(
                    icon = when (index) {
                        0 -> Icons.Default.Favorite
                        1 -> Icons.Default.DirectionsWalk
                        else -> Icons.Default.Bedtime
                    },
                    title = when (index) {
                        0 -> "Heart Rate Recorded"
                        1 -> "Daily Steps"
                        else -> "Sleep Tracked"
                    },
                    subtitle = when (index) {
                        0 -> "72 bpm • Today, 9:42 AM"
                        1 -> "8,432 steps • Today"
                        else -> "7.5 hrs • Last night"
                    }
                )
            }
        }
    }
}

// ═════════════════════════════════════════════════════
// TOP BAR - FIXED SPACING & PROFESSIONAL
// ═════════════════════════════════════════════════════

@Composable
fun DashboardTopBar() {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.xs),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Profile Section
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm)
        ) {
            // Avatar
            Surface(
                modifier = Modifier.size(44.dp),
                shape = CircleShape,
                color = MaterialTheme.colorScheme.primaryContainer
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = Icons.Default.Person,
                        contentDescription = "Profile",
                        tint = MaterialTheme.colorScheme.onPrimaryContainer,
                        modifier = Modifier.size(24.dp)
                    )
                }
            }

            // Text
            Column(
                verticalArrangement = Arrangement.spacedBy(2.dp)
            ) {
                Text(
                    text = "Health Guardian",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onBackground,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                Text(
                    text = "Your health, simplified",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }

        // Notification Button
        Surface(
            modifier = Modifier.size(42.dp),
            shape = CircleShape,
            color = MaterialTheme.colorScheme.surfaceVariant
        ) {
            IconButton(
                onClick = { },
                modifier = Modifier.padding(4.dp)
            ) {
                Icon(
                    imageVector = Icons.Outlined.Notifications,
                    contentDescription = "Notifications",
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(22.dp)
                )
            }
        }
    }
}

// ═════════════════════════════════════════════════════
// GREETING SECTION
// ═════════════════════════════════════════════════════

@Composable
fun GreetingSection() {
    Column(
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Text(
            text = "Good Morning, User 👋",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )

        Text(
            text = "Here's your health overview for today.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

// ═════════════════════════════════════════════════════
// HEALTH SCORE CARD
// ═════════════════════════════════════════════════════

@Composable
fun HealthScoreCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(CornerRadius.xl),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(Spacing.lg),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Score Circle
            Box(
                modifier = Modifier
                    .size(76.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primary),
                contentAlignment = Alignment.Center
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(2.dp)
                ) {
                    Text(
                        text = "86",
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimary
                    )

                    Text(
                        text = "/100",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                }
            }

            Spacer(modifier = Modifier.width(Spacing.lg))

            // Info
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(Spacing.xs)
            ) {
                Text(
                    text = "Today's Health Score",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )

                Text(
                    text = "You're doing great today!",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.TrendingUp,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(16.dp)
                    )

                    Text(
                        text = "+6% from yesterday",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
        }
    }
}

// ═════════════════════════════════════════════════════
// SECTION HEADER
// ═════════════════════════════════════════════════════

@Composable
fun SectionHeader(
    title: String,
    action: String? = null
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface
        )

        if (action != null) {
            TextButton(
                onClick = { },
                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
            ) {
                Text(
                    text = action,
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }
    }
}

// ═════════════════════════════════════════════════════
// HEALTH METRIC CARD - OPTIMIZED SIZE
// ═════════════════════════════════════════════════════

@Composable
fun HealthMetricCard(
    icon: ImageVector,
    metric: String,
    value: String,
    unit: String
) {
    Card(
        modifier = Modifier
            .width(145.dp)
            .height(135.dp),
        shape = RoundedCornerShape(CornerRadius.lg),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(Spacing.md),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // Icon Container
            Surface(
                modifier = Modifier.size(36.dp),
                shape = RoundedCornerShape(CornerRadius.md),
                color = MaterialTheme.colorScheme.primaryContainer
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = icon,
                        contentDescription = metric,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }

            // Values
            Column(
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Text(
                    text = metric,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                Row(
                    verticalAlignment = Alignment.Bottom,
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    Text(
                        text = value,
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1
                    )

                    Text(
                        text = unit,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1
                    )
                }
            }
        }
    }
}

// ═════════════════════════════════════════════════════
// AI GUARDIAN CARD
// ═════════════════════════════════════════════════════

@Composable
fun AIGuardianCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(CornerRadius.xl),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(Spacing.lg),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // AI Icon
            Surface(
                modifier = Modifier.size(52.dp),
                shape = CircleShape,
                color = TealPrimary
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = Icons.Default.SmartToy,
                        contentDescription = "AI Health Guardian",
                        tint = MaterialTheme.colorScheme.onPrimary,
                        modifier = Modifier.size(28.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.width(Spacing.md))

            // Content
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(Spacing.xs)
            ) {
                Text(
                    text = "AI Health Guardian",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )

                Text(
                    text = "Ask questions & get personalized guidance.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )

                Spacer(modifier = Modifier.height(Spacing.xs))

                Button(
                    onClick = { },
                    shape = RoundedCornerShape(CornerRadius.md),
                    contentPadding = PaddingValues(
                        horizontal = Spacing.md,
                        vertical = Spacing.sm
                    )
                ) {
                    Text(text = "Ask AI")
                    Spacer(modifier = Modifier.width(Spacing.xs))
                    Icon(
                        imageVector = Icons.Default.ArrowForward,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp)
                    )
                }
            }
        }
    }
}

// ═════════════════════════════════════════════════════
// QUICK ACTION BUTTON
// ═════════════════════════════════════════════════════

@Composable
fun QuickActionButton(
    icon: ImageVector,
    label: String,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.height(95.dp),
        shape = RoundedCornerShape(CornerRadius.lg),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        onClick = { }
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(Spacing.sm),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Surface(
                modifier = Modifier.size(38.dp),
                shape = CircleShape,
                color = MaterialTheme.colorScheme.primaryContainer
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = icon,
                        contentDescription = label,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(Spacing.xs))

            Text(
                text = label,
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

// ═════════════════════════════════════════════════════
// RECENT ACTIVITY CARD
// ═════════════════════════════════════════════════════

@Composable
fun RecentActivityCard(
    icon: ImageVector,
    title: String,
    subtitle: String
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(CornerRadius.lg),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(Spacing.md),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.md)
        ) {
            // Icon
            Surface(
                modifier = Modifier.size(42.dp),
                shape = CircleShape,
                color = MaterialTheme.colorScheme.primaryContainer
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = icon,
                        contentDescription = title,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(22.dp)
                    )
                }
            }

            // Text
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }

            // Arrow
            Icon(
                imageVector = Icons.Default.ChevronRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}