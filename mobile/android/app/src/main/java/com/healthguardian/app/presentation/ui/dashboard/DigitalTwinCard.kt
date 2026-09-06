package com.healthguardian.app.presentation.ui.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.MonitorHeart
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.healthguardian.app.domain.model.DigitalTwin
import com.healthguardian.app.domain.model.HealthState

@Composable
fun DigitalTwinCard(
    digitalTwin: DigitalTwin,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        )
    ) {
        Column(
            modifier = Modifier.padding(20.dp)
        ) {

            // ====================================================
            // HEADER
            // ====================================================

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Personal Health Twin",
                        style = MaterialTheme.typography.titleLarge
                    )

                    Spacer(
                        modifier = Modifier.height(4.dp)
                    )

                    Text(
                        text = "Your health state at a glance",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Icon(
                    imageVector = Icons.Default.MonitorHeart,
                    contentDescription = "Personal Health Twin"
                )
            }

            Spacer(
                modifier = Modifier.height(20.dp)
            )

            // ====================================================
            // OVERALL HEALTH STATE
            // ====================================================

            HealthStateRow(
                state = digitalTwin.overallState
            )

            Spacer(
                modifier = Modifier.height(20.dp)
            )

            // ====================================================
            // SUMMARY
            // ====================================================

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                TwinSummaryItem(
                    modifier = Modifier.weight(1f),
                    title = "Metrics",
                    value = digitalTwin.currentMetrics.size.toString()
                )

                TwinSummaryItem(
                    modifier = Modifier.weight(1f),
                    title = "Baselines",
                    value = digitalTwin.baselines.size.toString()
                )

                TwinSummaryItem(
                    modifier = Modifier.weight(1f),
                    title = "Trends",
                    value = digitalTwin.trends.size.toString()
                )
            }
        }
    }
}

// ================================================================
// HEALTH STATE
// ================================================================

@Composable
private fun HealthStateRow(
    state: HealthState
) {
    val label = when (state) {
        HealthState.STABLE -> "Stable"
        HealthState.IMPROVING -> "Improving"
        HealthState.NEEDS_ATTENTION -> "Needs Attention"
        HealthState.UNKNOWN -> "Unknown"
    }

    val icon = when (state) {
        HealthState.STABLE -> Icons.Default.Favorite
        HealthState.IMPROVING -> Icons.Default.TrendingUp
        HealthState.NEEDS_ATTENTION -> Icons.Default.MonitorHeart
        HealthState.UNKNOWN -> Icons.Default.MonitorHeart
    }

    Row(
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null
        )

        Spacer(
            modifier = Modifier.padding(horizontal = 6.dp)
        )

        Text(
            text = "Overall state: $label",
            style = MaterialTheme.typography.titleMedium
        )
    }
}

// ================================================================
// SUMMARY ITEM
// ================================================================

@Composable
private fun TwinSummaryItem(
    modifier: Modifier = Modifier,
    title: String,
    value: String
) {
    Column(
        modifier = modifier
    ) {
        Text(
            text = value,
            style = MaterialTheme.typography.titleLarge
        )

        Text(
            text = title,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}