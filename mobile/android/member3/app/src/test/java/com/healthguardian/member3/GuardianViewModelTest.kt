package com.healthguardian.member3

import com.healthguardian.member3.data.*
import com.healthguardian.member3.ui.GuardianViewModel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class GuardianViewModelTest {
    private class FakeApiClient : Member3Gateway {
        var askResult = "Explanation from AI assistant"
        var insightsList = listOf(HealthInsight("i1", "Sleep Recovery", "Good sleep", "active"))
        var alertsList = listOf(GuardianAlert("a1", "HR Alert", "Elevated HR", "high", "active"))
        var caregiversList = listOf(Caregiver("c1", "Dr. Smith", "active"))
        var emergencyResult = EmergencyWorkflow("w1", "initiated", "Confirm emergency call")

        override fun askAssistant(userId: String, question: String): String = askResult
        override fun listInsights(userId: String): List<HealthInsight> = insightsList
        override fun listAlerts(userId: String): List<GuardianAlert> = alertsList
        override fun listCaregivers(userId: String): List<Caregiver> = caregiversList
        override fun inviteCaregiver(
            userId: String,
            caregiverUserRef: String,
            relationshipLabel: String,
        ): Caregiver = Caregiver("c2", relationshipLabel, "pending")

        override fun startEmergency(userId: String, reason: String): EmergencyWorkflow =
            emergencyResult
    }

    @Test
    fun switchUserUpdatesStateAndSession() {
        val repository = Member3Repository(FakeApiClient())
        val session = InMemorySessionManager("user-a", "token-a")
        val viewModel = GuardianViewModel(repository, session)

        viewModel.switchUser("user-b", "token-b")

        assertEquals("user-b", viewModel.userId)
        assertEquals("user-b", viewModel.state.value.currentUserId)
    }

    @Test
    fun unauthenticatedUserShowsErrorOnRefresh() {
        val repository = Member3Repository(FakeApiClient())
        val viewModel = GuardianViewModel(repository, InMemorySessionManager())

        viewModel.refresh()

        assertTrue(viewModel.state.value.insights is LoadState.Error)
    }
}
