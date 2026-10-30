package com.healthguardian.app.presentation.ui.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.DirectionsWalk
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.MonitorWeight
import androidx.compose.material.icons.filled.Nightlight
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.healthguardian.app.domain.model.HealthMetric
import com.healthguardian.app.presentation.viewmodel.DigitalTwinUiState
import com.healthguardian.app.presentation.viewmodel.DigitalTwinViewModel

@Composable
fun DigitalTwinSection(
    modifier: Modifier = Modifier,
    viewModel: DigitalTwinViewModel = viewModel()
) {

    val uiState by viewModel.uiState.collectAsState()

    Column(
        modifier = modifier.fillMaxWidth()
    ) {

        when (val state = uiState) {

            DigitalTwinUiState.Loading -> {

                DigitalTwinLoading()
            }

            DigitalTwinUiState.Empty -> {

                DigitalTwinEmpty(
                    onRefresh = viewModel::loadDigitalTwin
                )
            }

            is DigitalTwinUiState.Error -> {

                DigitalTwinError(
                    message = state.message,
                    onRetry = viewModel::loadDigitalTwin
                )
            }

            is DigitalTwinUiState.Success -> {

                DigitalTwinContent(
                    digitalTwin = state.digitalTwin,
                    onRefresh = viewModel::loadDigitalTwin
                )
            }
        }
    }
}

@Composable
private fun DigitalTwinContent(
    digitalTwin: com.healthguardian.app.domain.model.DigitalTwin,
    onRefresh: () -> Unit
) {

    DigitalTwinCard(
        digitalTwin = digitalTwin
    )

    Spacer(
        modifier = Modifier.height(20.dp)
    )

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {

        Text(
            text = "Current Health",
            style = MaterialTheme.typography.titleLarge
        )

        AssistChip(
            onClick = onRefresh,
            label = {
                Text("Refresh")
            },
            leadingIcon = {
                Icon(
                    imageVector = Icons.Default.Refresh,
                    contentDescription = null
                )
            }
        )
    }

    Spacer(
        modifier = Modifier.height(12.dp)
    )

    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {

        items(
            items = digitalTwin.currentMetrics
        ) { metric ->

            MetricCard(
                metric = metric
            )
        }
    }

    Spacer(
        modifier = Modifier.height(20.dp)
    )

    BaselineSummary(
        digitalTwin = digitalTwin
    )

    Spacer(
        modifier = Modifier.height(20.dp)
    )

    TrendSummary(
        digitalTwin = digitalTwin
    )

    Spacer(
        modifier = Modifier.height(20.dp)
    )

    EventSummary(
        digitalTwin = digitalTwin
    )

    Spacer(
        modifier = Modifier.height(8.dp)
    )

    Text(
        text = "Development data • Replace with backend data during integration.",
        style = MaterialTheme.typography.labelSmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.padding(horizontal = 4.dp)
    )
}

@Composable
private fun MetricCard(
    metric: HealthMetric
) {

    val icon = when (metric.type) {
        "Heart Rate" -> Icons.Default.Favorite
        "Sleep" -> Icons.Default.Nightlight
        "Steps" -> Icons.Default.DirectionsWalk
        "Weight" -> Icons.Default.MonitorWeight
        else -> Icons.Default.AccessTime
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {

        Column(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth()
        ) {

            Icon(
                imageVector = icon,
                contentDescription = metric.type
            )

            Spacer(
                modifier = Modifier.height(10.dp)
            )

            Text(
                text = metric.type,
                style = MaterialTheme.typography.labelLarge
            )

            Text(
                text = formatMetric(metric),
                style = MaterialTheme.typography.titleLarge
            )
        }
    }
}

private fun formatMetric(
    metric: HealthMetric
): String {

    val value = if (metric.value % 1.0 == 0.0) {
        metric.value.toInt().toString()
    } else {
        "%.1f".format(metric.value)
    }

    return "$value ${metric.unit}"
}

@Composable
private fun BaselineSummary(
    digitalTwin: com.healthguardian.app.domain.model.DigitalTwin
) {

    Column {

        Text(
            text = "Personal Baselines",
            style = MaterialTheme.typography.titleLarge
        )

        Spacer(
            modifier = Modifier.height(10.dp)
        )

        digitalTwin.baselines.forEach { baseline ->

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 8.dp)
            ) {

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {

                    Column {

                        Text(
                            text = baseline.metricType,
                            style = MaterialTheme.typography.titleMedium
                        )

                        Text(
                            text = "Baseline: ${baseline.baselineValue} ${baseline.unit}",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }

                    Text(
                        text = baseline.status.name
                            .replace("_", " "),
                        style = MaterialTheme.typography.labelMedium
                    )
                }
            }
        }
    }
}

@Composable
private fun TrendSummary(
    digitalTwin: com.healthguardian.app.domain.model.DigitalTwin
) {

    Column {

        Text(
            text = "Health Trends",
            style = MaterialTheme.typography.titleLarge
        )

        Spacer(
            modifier = Modifier.height(10.dp)
        )

        digitalTwin.trends.forEach { trend ->

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 8.dp)
            ) {

                Column(
                    modifier = Modifier.padding(14.dp)
                ) {

                    Text(
                        text = trend.metricType,
                        style = MaterialTheme.typography.titleMedium
                    )

                    Text(
                        text = trend.direction.name
                            .replace("_", " "),
                        style = MaterialTheme.typography.labelMedium
                    )

                    trend.changePercentage?.let {

                        Text(
                            text = "${if (it >= 0) "+" else ""}%.1f%% over ${trend.period}"
                                .format(it),
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }

                    trend.description?.let {

                        Text(
                            text = it,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun EventSummary(
    digitalTwin: com.healthguardian.app.domain.model.DigitalTwin
) {

    Column {

        Text(
            text = "Recent Health Events",
            style = MaterialTheme.typography.titleLarge
        )

        Spacer(
            modifier = Modifier.height(10.dp)
        )

        digitalTwin.recentEvents.forEach { event ->

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 8.dp)
            ) {

                Column(
                    modifier = Modifier.padding(14.dp)
                ) {

                    Text(
                        text = event.metricType,
                        style = MaterialTheme.typography.titleMedium
                    )

                    Text(
                        text = "${event.value ?: "--"} ${event.unit ?: ""}",
                        style = MaterialTheme.typography.bodyMedium
                    )

                    Text(
                        text = "Source: ${event.source}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

@Composable
private fun DigitalTwinLoading() {

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 40.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {

        CircularProgressIndicator()

        Spacer(
            modifier = Modifier.height(12.dp)
        )

        Text(
            text = "Loading your health twin..."
        )
    }
}

@Composable
private fun DigitalTwinEmpty(
    onRefresh: () -> Unit
) {

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 30.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {

        Text(
            text = "No health data available",
            style = MaterialTheme.typography.titleMedium
        )

        Spacer(
            modifier = Modifier.height(12.dp)
        )

        Button(
            onClick = onRefresh
        ) {
            Text("Refresh")
        }
    }
}

@Composable
private fun DigitalTwinError(
    message: String,
    onRetry: () -> Unit
) {

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 30.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {

        Text(
            text = "Unable to load health data",
            style = MaterialTheme.typography.titleMedium
        )

        Spacer(
            modifier = Modifier.height(8.dp)
        )

        Text(
            text = message,
            style = MaterialTheme.typography.bodySmall
        )

        Spacer(
            modifier = Modifier.height(12.dp)
        )

        Button(
            onClick = onRetry
        ) {
            Text("Try Again")
        }
    }
}