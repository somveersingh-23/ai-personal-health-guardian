package com.healthguardian.app.presentation.ui.insights

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.FilterList
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.healthguardian.app.core.ui.theme.ErrorColor
import com.healthguardian.app.core.ui.theme.SuccessColor
import com.healthguardian.app.core.ui.theme.WarningColor


// ============================================================
// INSIGHTS SCREEN
// ============================================================

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InsightsScreen(
    onBackClick: () -> Unit = {},
    onInsightClick: (InsightItem) -> Unit = {}
) {

    // --------------------------------------------------------
    // Insight data
    // --------------------------------------------------------

    val insights = remember {

        listOf(

            InsightItem(
                id = "1",
                title = "Sleep Pattern",
                description = "Your sleep duration has been consistent",
                severity = "low",
                timestamp = "2 hours ago"
            ),

            InsightItem(
                id = "2",
                title = "Activity Level",
                description = "You've been more active than usual",
                severity = "moderate",
                timestamp = "1 day ago"
            ),

            InsightItem(
                id = "3",
                title = "Heart Health",
                description = "Your recent heart rate is within your normal range",
                severity = "low",
                timestamp = "2 days ago"
            ),

            InsightItem(
                id = "4",
                title = "Hydration",
                description = "Your recorded water intake is below your usual level",
                severity = "moderate",
                timestamp = "3 days ago"
            ),

            InsightItem(
                id = "5",
                title = "Health Check",
                description = "Consider reviewing your latest health measurements",
                severity = "high",
                timestamp = "1 week ago"
            )
        )
    }


    // ========================================================
    // SCAFFOLD
    // ========================================================

    Scaffold(

        modifier = Modifier.fillMaxSize(),

        // ----------------------------------------------------
        // Top bar
        // ----------------------------------------------------

        topBar = {

            InsightsTopBar(
                onBackClick = onBackClick
            )
        },

        // ----------------------------------------------------
        // Keep Scaffold from adding another system inset.
        //
        // CenterAlignedTopAppBar handles the status bar itself.
        // ----------------------------------------------------

        contentWindowInsets =
            WindowInsets(0, 0, 0, 0)

    ) { innerPadding ->


        // ====================================================
        // SCROLLABLE CONTENT
        // ====================================================

        LazyColumn(

            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),

            contentPadding = PaddingValues(

                start = 16.dp,
                end = 16.dp,

                top = 14.dp,

                // Large bottom padding ensures that the last
                // insight can scroll above your bottom navigation.
                bottom = 130.dp
            ),

            verticalArrangement =
                Arrangement.spacedBy(12.dp)
        ) {


            // =================================================
            // PAGE HEADER
            // =================================================

            item {

                InsightsHeader()
            }


            // =================================================
            // OVERVIEW CARD
            // =================================================

            item {

                InsightsOverviewCard(
                    count = insights.size
                )
            }


            // =================================================
            // SECTION HEADER
            // =================================================

            item {

                InsightsSectionHeader(
                    count = insights.size
                )
            }


            // =================================================
            // INSIGHT CARDS
            // =================================================

            items(

                items = insights,

                key = {
                    it.id
                }

            ) { insight ->

                InsightCard(

                    insight = insight,

                    onClick = {
                        onInsightClick(insight)
                    }
                )
            }
        }
    }
}


// ============================================================
// TOP APP BAR
// ============================================================

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun InsightsTopBar(
    onBackClick: () -> Unit
) {

    CenterAlignedTopAppBar(

        title = {

            Column(

                horizontalAlignment =
                    Alignment.CenterHorizontally
            ) {

                Text(

                    text = "Health Insights",

                    style =
                        MaterialTheme.typography.titleLarge,

                    fontWeight =
                        FontWeight.Bold,

                    color =
                        MaterialTheme.colorScheme.onBackground
                )

                Text(

                    text = "Personalized health information",

                    style =
                        MaterialTheme.typography.labelSmall,

                    color =
                        MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        },


        // ----------------------------------------------------
        // Back button
        // ----------------------------------------------------

        navigationIcon = {

            IconButton(
                onClick = onBackClick
            ) {

                Icon(

                    imageVector =
                        Icons.Default.ArrowBack,

                    contentDescription =
                        "Back",

                    tint =
                        MaterialTheme.colorScheme.onSurface
                )
            }
        },


        // ----------------------------------------------------
        // Refresh action
        // ----------------------------------------------------

        actions = {

            IconButton(
                onClick = {
                    // TODO:
                    // Refresh insights from ViewModel
                }
            ) {

                Icon(

                    imageVector =
                        Icons.Default.Refresh,

                    contentDescription =
                        "Refresh insights",

                    tint =
                        MaterialTheme.colorScheme.primary
                )
            }
        },


        colors =
            TopAppBarDefaults.centerAlignedTopAppBarColors(

                containerColor =
                    MaterialTheme.colorScheme.background,

                titleContentColor =
                    MaterialTheme.colorScheme.onBackground,

                navigationIconContentColor =
                    MaterialTheme.colorScheme.onSurface,

                actionIconContentColor =
                    MaterialTheme.colorScheme.primary
            )
    )
}


// ============================================================
// HEADER
// ============================================================

@Composable
private fun InsightsHeader() {

    Column(

        modifier = Modifier
            .fillMaxWidth()
            .padding(
                top = 2.dp,
                bottom = 2.dp
            ),

        verticalArrangement =
            Arrangement.spacedBy(4.dp)
    ) {

        Text(

            text = "Health Insights",

            style =
                MaterialTheme.typography.headlineSmall,

            fontWeight =
                FontWeight.Bold,

            color =
                MaterialTheme.colorScheme.onBackground
        )

        Text(

            text =
                "Personalized insights based on your health data",

            style =
                MaterialTheme.typography.bodyMedium,

            color =
                MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}


// ============================================================
// OVERVIEW CARD
// ============================================================

@Composable
private fun InsightsOverviewCard(
    count: Int
) {

    Card(

        modifier =
            Modifier.fillMaxWidth(),

        shape =
            RoundedCornerShape(18.dp),

        colors =
            CardDefaults.cardColors(

                containerColor =
                    MaterialTheme.colorScheme.primaryContainer
            ),

        elevation =
            CardDefaults.cardElevation(
                defaultElevation = 0.dp
            )
    ) {

        Row(

            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),

            verticalAlignment =
                Alignment.CenterVertically
        ) {


            // ------------------------------------------------
            // Lightbulb icon
            // ------------------------------------------------

            Surface(

                modifier =
                    Modifier.size(46.dp),

                shape =
                    CircleShape,

                color =
                    MaterialTheme.colorScheme.primary
                        .copy(alpha = 0.12f)
            ) {

                Box(

                    contentAlignment =
                        Alignment.Center
                ) {

                    Icon(

                        imageVector =
                            Icons.Default.Lightbulb,

                        contentDescription = null,

                        tint =
                            MaterialTheme.colorScheme.primary,

                        modifier =
                            Modifier.size(23.dp)
                    )
                }
            }


            Spacer(
                modifier =
                    Modifier.width(14.dp)
            )


            // ------------------------------------------------
            // Text
            // ------------------------------------------------

            Column(
                modifier =
                    Modifier.weight(1f)
            ) {

                Text(

                    text =
                        "$count insights available",

                    style =
                        MaterialTheme.typography.titleMedium,

                    fontWeight =
                        FontWeight.Bold,

                    color =
                        MaterialTheme.colorScheme
                            .onPrimaryContainer
                )

                Spacer(
                    modifier =
                        Modifier.height(2.dp)
                )

                Text(

                    text =
                        "Review patterns and updates from your health data",

                    style =
                        MaterialTheme.typography.bodySmall,

                    color =
                        MaterialTheme.colorScheme
                            .onPrimaryContainer
                            .copy(alpha = 0.70f),

                    maxLines = 2,

                    overflow =
                        TextOverflow.Ellipsis
                )
            }
        }
    }
}


// ============================================================
// SECTION HEADER
// ============================================================

@Composable
private fun InsightsSectionHeader(
    count: Int
) {

    Row(

        modifier = Modifier
            .fillMaxWidth()
            .padding(
                top = 4.dp,
                start = 2.dp,
                end = 2.dp
            ),

        horizontalArrangement =
            Arrangement.SpaceBetween,

        verticalAlignment =
            Alignment.CenterVertically
    ) {

        Text(

            text = "Recent insights",

            style =
                MaterialTheme.typography.titleMedium,

            fontWeight =
                FontWeight.Bold,

            color =
                MaterialTheme.colorScheme.onBackground
        )


        Surface(

            shape =
                RoundedCornerShape(50.dp),

            color =
                MaterialTheme.colorScheme.primaryContainer
        ) {

            Text(

                text = "$count total",

                modifier =
                    Modifier.padding(
                        horizontal = 10.dp,
                        vertical = 5.dp
                    ),

                style =
                    MaterialTheme.typography.labelMedium,

                fontWeight =
                    FontWeight.SemiBold,

                color =
                    MaterialTheme.colorScheme.primary
            )
        }
    }
}


// ============================================================
// INSIGHT CARD
// ============================================================

@Composable
fun InsightCard(

    insight: InsightItem,

    onClick: () -> Unit = {}
) {

    val icon =
        when (insight.severity.lowercase()) {

            "high" ->
                Icons.Default.Error

            "moderate" ->
                Icons.Default.Warning

            else ->
                Icons.Default.Lightbulb
        }


    val accentColor =
        when (insight.severity.lowercase()) {

            "high" ->
                ErrorColor

            "moderate" ->
                WarningColor

            else ->
                SuccessColor
        }


    val backgroundColor =
        when (insight.severity.lowercase()) {

            "high" ->
                ErrorColor.copy(alpha = 0.08f)

            "moderate" ->
                WarningColor.copy(alpha = 0.10f)

            else ->
                SuccessColor.copy(alpha = 0.10f)
        }


    Card(

        modifier =
            Modifier.fillMaxWidth(),

        onClick = onClick,

        shape =
            RoundedCornerShape(18.dp),

        colors =
            CardDefaults.cardColors(

                containerColor =
                    backgroundColor
            ),

        elevation =
            CardDefaults.cardElevation(
                defaultElevation = 0.dp,
                pressedElevation = 2.dp
            )
    ) {

        Row(

            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),

            verticalAlignment =
                Alignment.CenterVertically
        ) {


            // =================================================
            // ICON
            // =================================================

            Surface(

                modifier =
                    Modifier.size(48.dp),

                shape =
                    RoundedCornerShape(14.dp),

                color =
                    accentColor.copy(alpha = 0.12f)
            ) {

                Box(

                    contentAlignment =
                        Alignment.Center
                ) {

                    Icon(

                        imageVector =
                            icon,

                        contentDescription = null,

                        tint =
                            accentColor,

                        modifier =
                            Modifier.size(23.dp)
                    )
                }
            }


            Spacer(
                modifier =
                    Modifier.width(14.dp)
            )


            // =================================================
            // CONTENT
            // =================================================

            Column(

                modifier =
                    Modifier.weight(1f),

                verticalArrangement =
                    Arrangement.spacedBy(3.dp)
            ) {

                // ---------------------------------------------
                // Title + severity
                // ---------------------------------------------

                Row(

                    verticalAlignment =
                        Alignment.CenterVertically,

                    horizontalArrangement =
                        Arrangement.spacedBy(7.dp)
                ) {

                    Text(

                        text =
                            insight.title,

                        style =
                            MaterialTheme.typography.titleMedium,

                        fontWeight =
                            FontWeight.SemiBold,

                        color =
                            MaterialTheme.colorScheme.onSurface,

                        maxLines = 1,

                        overflow =
                            TextOverflow.Ellipsis,

                        modifier =
                            Modifier.weight(1f)
                    )


                    // Severity pill

                    Surface(

                        shape =
                            RoundedCornerShape(50.dp),

                        color =
                            accentColor.copy(
                                alpha = 0.12f
                            )
                    ) {

                        Text(

                            text =
                                insight.severity
                                    .replaceFirstChar {
                                        it.uppercase()
                                    },

                            modifier =
                                Modifier.padding(
                                    horizontal = 8.dp,
                                    vertical = 4.dp
                                ),

                            style =
                                MaterialTheme.typography.labelSmall,

                            fontWeight =
                                FontWeight.SemiBold,

                            color =
                                accentColor
                        )
                    }
                }


                // ---------------------------------------------
                // Description
                // ---------------------------------------------

                Text(

                    text =
                        insight.description,

                    style =
                        MaterialTheme.typography.bodyMedium,

                    color =
                        MaterialTheme.colorScheme.onSurfaceVariant,

                    maxLines = 2,

                    overflow =
                        TextOverflow.Ellipsis
                )


                Spacer(
                    modifier =
                        Modifier.height(1.dp)
                )


                // ---------------------------------------------
                // Timestamp
                // ---------------------------------------------

                Text(

                    text =
                        insight.timestamp,

                    style =
                        MaterialTheme.typography.labelSmall,

                    color =
                        MaterialTheme.colorScheme
                            .onSurfaceVariant
                            .copy(alpha = 0.70f)
                )
            }


            Spacer(
                modifier =
                    Modifier.width(6.dp)
            )


            // =================================================
            // ARROW
            // =================================================

            Icon(

                imageVector =
                    Icons.Default.ChevronRight,

                contentDescription =
                    "View ${insight.title}",

                tint =
                    MaterialTheme.colorScheme
                        .onSurfaceVariant,

                modifier =
                    Modifier.size(20.dp)
            )
        }
    }
}


// ============================================================
// DATA MODEL
// ============================================================

data class InsightItem(

    val id: String,

    val title: String,

    val description: String,

    val severity: String,

    val timestamp: String
)