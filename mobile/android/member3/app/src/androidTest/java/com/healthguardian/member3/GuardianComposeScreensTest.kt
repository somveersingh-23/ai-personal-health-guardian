package com.healthguardian.member3

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import com.healthguardian.member3.data.*
import com.healthguardian.member3.ui.*
import org.junit.Rule
import org.junit.Test

class GuardianComposeScreensTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun assistantScreenDisplaysHeaderAndDisclaimer() {
        composeTestRule.setContent {
            AssistantScreen(
                messages = emptyList(),
                loadState = LoadState.Idle,
                send = {},
            )
        }
        composeTestRule.onNodeWithText("Ask about your health changes").assertIsDisplayed()
        composeTestRule.onNodeWithText("This assistant provides information, not a diagnosis. For urgent symptoms, contact local emergency services.").assertIsDisplayed()
    }

    @Test
    fun insightsScreenDisplaysEmptyState() {
        composeTestRule.setContent {
            InsightsScreen(
                state = LoadState.Ready(emptyList()),
                retry = {},
            )
        }
        composeTestRule.onNodeWithText("Health insights").assertIsDisplayed()
        composeTestRule.onNodeWithText("No new insights. Your meaningful changes will appear here.").assertIsDisplayed()
    }

    @Test
    fun alertsScreenDisplaysAlertCards() {
        val alerts = listOf(
            GuardianAlert("alt-1", "Resting HR Elevated", "Higher than 30d baseline", "critical", "active")
        )
        composeTestRule.setContent {
            AlertsScreen(
                state = LoadState.Ready(alerts),
                retry = {},
            )
        }
        composeTestRule.onNodeWithText("Resting HR Elevated").assertIsDisplayed()
        composeTestRule.onNodeWithText("Higher than 30d baseline").assertIsDisplayed()
    }

    @Test
    fun emergencyScreenDisplaysWarningAndConfirmRequirement() {
        composeTestRule.setContent {
            EmergencyScreen(
                caregivers = LoadState.Ready(emptyList()),
                emergency = LoadState.Idle,
                start = {},
                retry = {},
            )
        }
        composeTestRule.onNodeWithText("Emergency and caregivers").assertIsDisplayed()
        composeTestRule.onNodeWithText("The app never calls emergency services automatically. You must review and confirm every escalation.").assertIsDisplayed()
    }
}
