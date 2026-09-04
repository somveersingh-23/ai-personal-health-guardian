package com.healthguardian.app.presentation.ui.records

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
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
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Assignment
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.FilterList
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.MedicalServices
import androidx.compose.material.icons.filled.MonitorWeight
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.healthguardian.app.core.ui.theme.CornerRadius
import com.healthguardian.app.core.ui.theme.Spacing


// ============================================================
// HEALTH RECORDS SCREEN
// ============================================================

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HealthRecordsScreen(
    onAddRecord: () -> Unit = {},
    onRecordClick: (HealthRecordItem) -> Unit = {},
    onBackClick: () -> Unit = {}
) {

    // --------------------------------------------------------
    // Sample records
    // Replace these later with your ViewModel/database data.
    // --------------------------------------------------------

    val records = remember {
        listOf(

            HealthRecordItem(
                id = "1",
                title = "Blood Pressure",
                type = "Measurement",
                value = "120/80 mmHg",
                timestamp = "2 hours ago",
                icon = Icons.Default.Favorite,
                iconTint = Color(0xFFD84B68),
                iconBackground = Color(0xFFFFE4EA)
            ),

            HealthRecordItem(
                id = "2",
                title = "Weight Check",
                type = "Measurement",
                value = "70 kg",
                timestamp = "1 day ago",
                icon = Icons.Default.MonitorWeight,
                iconTint = Color(0xFF5874C8),
                iconBackground = Color(0xFFE8EDFF)
            ),

            HealthRecordItem(
                id = "3",
                title = "Regular Checkup",
                type = "Doctor Visit",
                value = "Annual physical",
                timestamp = "1 week ago",
                icon = Icons.Default.MedicalServices,
                iconTint = Color(0xFF0D9488),
                iconBackground = Color(0xFFDDF7F3)
            ),

            HealthRecordItem(
                id = "4",
                title = "Blood Sugar",
                type = "Measurement",
                value = "96 mg/dL",
                timestamp = "2 weeks ago",
                icon = Icons.Default.Favorite,
                iconTint = Color(0xFF8B5CF6),
                iconBackground = Color(0xFFF0E9FF)
            ),

            HealthRecordItem(
                id = "5",
                title = "Heart Rate",
                type = "Measurement",
                value = "72 BPM",
                timestamp = "3 weeks ago",
                icon = Icons.Default.Favorite,
                iconTint = Color(0xFFE05270),
                iconBackground = Color(0xFFFFE8ED)
            ),

            HealthRecordItem(
                id = "6",
                title = "Doctor Consultation",
                type = "Doctor Visit",
                value = "General consultation",
                timestamp = "1 month ago",
                icon = Icons.Default.MedicalServices,
                iconTint = Color(0xFF0D9488),
                iconBackground = Color(0xFFDDF7F3)
            ),

            HealthRecordItem(
                id = "7",
                title = "Temperature",
                type = "Measurement",
                value = "98.6 °F",
                timestamp = "1 month ago",
                icon = Icons.Default.Favorite,
                iconTint = Color(0xFFE67E22),
                iconBackground = Color(0xFFFFEBDD)
            )
        )
    }


    // --------------------------------------------------------
    // Search state
    // --------------------------------------------------------

    var searchQuery by remember {
        mutableStateOf("")
    }


    // --------------------------------------------------------
    // Filter records
    // --------------------------------------------------------

    val filteredRecords = records.filter { record ->

        record.title.contains(
            searchQuery,
            ignoreCase = true
        ) ||

                record.type.contains(
                    searchQuery,
                    ignoreCase = true
                ) ||

                record.value.contains(
                    searchQuery,
                    ignoreCase = true
                )
    }


    // ========================================================
    // SCAFFOLD
    // ========================================================

    Scaffold(

        modifier = Modifier
            .fillMaxSize()
            .background(
                MaterialTheme.colorScheme.background
            ),

        // ----------------------------------------------------
        // Top App Bar
        //
        // Material 3 handles the status-bar inset here.
        // Do NOT add statusBarsPadding() to the TopAppBar.
        // ----------------------------------------------------

        topBar = {

            RecordsTopBar(
                onBackClick = onBackClick
            )
        },


        // ----------------------------------------------------
        // Floating Action Button
        //
        // navigationBarsPadding() keeps it above Android's
        // navigation/system area.
        //
        // Extra bottom padding keeps it above your app's
        // bottom navigation.
        // ----------------------------------------------------

        floatingActionButton = {

            FloatingActionButton(

                onClick = onAddRecord,

                modifier = Modifier
                    .navigationBarsPadding()
                    .padding(
                        bottom = 68.dp,
                        end = 4.dp
                    ),

                shape = CircleShape,

                containerColor =
                    MaterialTheme.colorScheme.primary,

                contentColor =
                    MaterialTheme.colorScheme.onPrimary
            ) {

                Icon(
                    imageVector = Icons.Default.Add,
                    contentDescription = "Add health record",
                    modifier = Modifier.size(26.dp)
                )
            }
        },

        // ----------------------------------------------------
        // Don't manually create status/navigation bars here.
        // Android will display the actual time/network/battery.
        // ----------------------------------------------------

        contentWindowInsets = WindowInsets(0, 0, 0, 0)

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

                // Space below top bar
                top = 14.dp,

                // IMPORTANT:
                // Large bottom padding prevents the last card
                // from disappearing behind bottom navigation/FAB.
                bottom = 150.dp
            ),

            verticalArrangement =
                Arrangement.spacedBy(12.dp)
        ) {


            // =================================================
            // HEADER
            // =================================================

            item {

                RecordsIntro()
            }


            // =================================================
            // SEARCH
            // =================================================

            item {

                RecordsSearchBar(
                    query = searchQuery,
                    onQueryChange = {
                        searchQuery = it
                    }
                )
            }


            // =================================================
            // SUMMARY
            // =================================================

            item {

                RecordsSummary(
                    recordsCount = filteredRecords.size
                )
            }


            // =================================================
            // SECTION HEADER
            // =================================================

            item {

                RecordsSectionHeader(
                    count = filteredRecords.size
                )
            }


            // =================================================
            // EMPTY STATE
            // =================================================

            if (filteredRecords.isEmpty()) {

                item {

                    RecordsEmptyState()
                }

            } else {


                // =============================================
                // RECORD CARDS
                // =============================================

                items(

                    items = filteredRecords,

                    key = {
                        it.id
                    }

                ) { record ->

                    HealthRecordCard(

                        record = record,

                        onClick = {
                            onRecordClick(record)
                        }
                    )
                }
            }
        }
    }
}


// ============================================================
// TOP APP BAR
// ============================================================

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun RecordsTopBar(
    onBackClick: () -> Unit
) {

    CenterAlignedTopAppBar(

        title = {

            Column(
                horizontalAlignment =
                    Alignment.CenterHorizontally
            ) {

                Text(
                    text = "Health Records",

                    style =
                        MaterialTheme.typography.titleLarge,

                    fontWeight =
                        FontWeight.Bold,

                    color =
                        MaterialTheme.colorScheme.onBackground
                )

                Text(
                    text = "Your health timeline",

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
        // Filter button
        // ----------------------------------------------------

        actions = {

            IconButton(
                onClick = {
                    // TODO:
                    // Open filter bottom sheet/dialog
                }
            ) {

                Icon(
                    imageVector =
                        Icons.Default.FilterList,

                    contentDescription =
                        "Filter records",

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
// INTRO HEADER
// ============================================================

@Composable
private fun RecordsIntro() {

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

            text = "Your health",

            style =
                MaterialTheme.typography.headlineSmall,

            fontWeight =
                FontWeight.Bold,

            color =
                MaterialTheme.colorScheme.onBackground
        )

        Text(

            text =
                "Track your measurements and medical visits",

            style =
                MaterialTheme.typography.bodyMedium,

            color =
                MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}


// ============================================================
// SEARCH BAR
// ============================================================

@Composable
private fun RecordsSearchBar(

    query: String,

    onQueryChange: (String) -> Unit
) {

    OutlinedTextField(

        value = query,

        onValueChange = onQueryChange,

        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp),

        singleLine = true,

        placeholder = {

            Text(
                text = "Search health records"
            )
        },

        leadingIcon = {

            Icon(
                imageVector =
                    Icons.Default.Search,

                contentDescription =
                    "Search",

                tint =
                    MaterialTheme.colorScheme.onSurfaceVariant
            )
        },

        shape =
            RoundedCornerShape(18.dp),

        colors =
            OutlinedTextFieldDefaults.colors(

                unfocusedContainerColor =
                    MaterialTheme.colorScheme.surface,

                focusedContainerColor =
                    MaterialTheme.colorScheme.surface,

                unfocusedBorderColor =
                    MaterialTheme.colorScheme.outline
                        .copy(alpha = 0.30f),

                focusedBorderColor =
                    MaterialTheme.colorScheme.primary,

                cursorColor =
                    MaterialTheme.colorScheme.primary
            )
    )
}


// ============================================================
// SUMMARY CARD
// ============================================================

@Composable
private fun RecordsSummary(
    recordsCount: Int
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
            // Icon
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
                            Icons.Default.Assignment,

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
                        "$recordsCount health records",

                    style =
                        MaterialTheme.typography.titleMedium,

                    fontWeight =
                        FontWeight.Bold,

                    color =
                        MaterialTheme.colorScheme.onPrimaryContainer
                )

                Spacer(
                    modifier =
                        Modifier.height(2.dp)
                )

                Text(

                    text =
                        "Everything is organized in one place",

                    style =
                        MaterialTheme.typography.bodySmall,

                    color =
                        MaterialTheme.colorScheme
                            .onPrimaryContainer
                            .copy(alpha = 0.70f)
                )
            }
        }
    }
}


// ============================================================
// SECTION HEADER
// ============================================================

@Composable
private fun RecordsSectionHeader(
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

            text = "Recent records",

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
                MaterialTheme.colorScheme
                    .primaryContainer
        ) {

            Text(

                text = "$count total",

                modifier = Modifier.padding(
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
// HEALTH RECORD CARD
// ============================================================

@Composable
fun HealthRecordCard(

    record: HealthRecordItem,

    onClick: () -> Unit = {}
) {

    Card(

        modifier = Modifier
            .fillMaxWidth()
            .animateContentSize(),

        onClick = onClick,

        shape =
            RoundedCornerShape(18.dp),

        colors =
            CardDefaults.cardColors(

                containerColor =
                    MaterialTheme.colorScheme.surface
            ),

        elevation =
            CardDefaults.cardElevation(

                defaultElevation = 1.dp,

                pressedElevation = 3.dp
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
            // RECORD ICON
            // =================================================

            Surface(

                modifier =
                    Modifier.size(50.dp),

                shape =
                    RoundedCornerShape(15.dp),

                color =
                    record.iconBackground
            ) {

                Box(

                    contentAlignment =
                        Alignment.Center
                ) {

                    Icon(

                        imageVector =
                            record.icon,

                        contentDescription =
                            record.title,

                        tint =
                            record.iconTint,

                        modifier =
                            Modifier.size(24.dp)
                    )
                }
            }


            Spacer(
                modifier =
                    Modifier.width(14.dp)
            )


            // =================================================
            // RECORD INFORMATION
            // =================================================

            Column(

                modifier =
                    Modifier.weight(1f),

                verticalArrangement =
                    Arrangement.spacedBy(2.dp)
            ) {

                Text(

                    text =
                        record.title,

                    style =
                        MaterialTheme.typography.titleMedium,

                    fontWeight =
                        FontWeight.SemiBold,

                    color =
                        MaterialTheme.colorScheme.onSurface,

                    maxLines = 1,

                    overflow =
                        TextOverflow.Ellipsis
                )


                Text(

                    text =
                        record.type,

                    style =
                        MaterialTheme.typography.labelMedium,

                    color =
                        MaterialTheme.colorScheme
                            .onSurfaceVariant,

                    maxLines = 1
                )


                Spacer(
                    modifier =
                        Modifier.height(2.dp)
                )


                Text(

                    text =
                        record.value,

                    style =
                        MaterialTheme.typography.bodyMedium,

                    fontWeight =
                        FontWeight.Bold,

                    color =
                        MaterialTheme.colorScheme.primary,

                    maxLines = 1,

                    overflow =
                        TextOverflow.Ellipsis
                )
            }


            Spacer(
                modifier =
                    Modifier.width(8.dp)
            )


            // =================================================
            // TIMESTAMP + ARROW
            // =================================================

            Column(

                horizontalAlignment =
                    Alignment.End,

                verticalArrangement =
                    Arrangement.spacedBy(5.dp)
            ) {

                Icon(

                    imageVector =
                        Icons.Default.ChevronRight,

                    contentDescription =
                        "Open ${record.title}",

                    tint =
                        MaterialTheme.colorScheme
                            .onSurfaceVariant,

                    modifier =
                        Modifier.size(20.dp)
                )


                Text(

                    text =
                        record.timestamp,

                    style =
                        MaterialTheme.typography.labelSmall,

                    color =
                        MaterialTheme.colorScheme
                            .onSurfaceVariant,

                    maxLines = 1,

                    overflow =
                        TextOverflow.Ellipsis
                )
            }
        }
    }
}


// ============================================================
// EMPTY STATE
// ============================================================

@Composable
private fun RecordsEmptyState() {

    Column(

        modifier = Modifier
            .fillMaxWidth()
            .padding(
                top = 50.dp,
                bottom = 40.dp
            ),

        horizontalAlignment =
            Alignment.CenterHorizontally,

        verticalArrangement =
            Arrangement.spacedBy(8.dp)
    ) {


        Surface(

            modifier =
                Modifier.size(72.dp),

            shape =
                CircleShape,

            color =
                MaterialTheme.colorScheme.primaryContainer
        ) {

            Box(

                contentAlignment =
                    Alignment.Center
            ) {

                Icon(

                    imageVector =
                        Icons.Default.Assignment,

                    contentDescription = null,

                    tint =
                        MaterialTheme.colorScheme.primary,

                    modifier =
                        Modifier.size(34.dp)
                )
            }
        }


        Spacer(
            modifier =
                Modifier.height(4.dp)
        )


        Text(

            text = "No records found",

            style =
                MaterialTheme.typography.titleMedium,

            fontWeight =
                FontWeight.SemiBold,

            color =
                MaterialTheme.colorScheme.onBackground
        )


        Text(

            text =
                "Try another search or add a new health record.",

            style =
                MaterialTheme.typography.bodyMedium,

            color =
                MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}


// ============================================================
// DATA MODEL
// ============================================================

data class HealthRecordItem(

    val id: String,

    val title: String,

    val type: String,

    val value: String,

    val timestamp: String,

    val icon: ImageVector =
        Icons.Default.Assignment,

    val iconTint: Color =
        Color(0xFF0D9488),

    val iconBackground: Color =
        Color(0xFFDDF7F3)
)