package com.healthguardian.member3

import com.healthguardian.member3.data.GuardianAlert
import com.healthguardian.member3.data.HealthInsight
import com.healthguardian.member3.data.InMemoryGuardianCache
import org.junit.Assert.*
import org.junit.Test

class LocalCacheTest {

    @Test
    fun cacheSavesAndRetrievesInsights() {
        val cache = InMemoryGuardianCache()
        val insights = listOf(
            HealthInsight(id = "ins-1", title = "Insight 1", summary = "Summary 1", status = "active")
        )
        cache.saveInsights("user-1", insights)
        val retrieved = cache.getInsights("user-1")
        assertEquals(1, retrieved.size)
        assertEquals("ins-1", retrieved[0].id)
    }

    @Test
    fun cacheSavesAndRetrievesAlerts() {
        val cache = InMemoryGuardianCache()
        val alerts = listOf(
            GuardianAlert(id = "alt-1", title = "Alert 1", message = "Msg 1", priority = "high", status = "active")
        )
        cache.saveAlerts("user-1", alerts)
        val retrieved = cache.getAlerts("user-1")
        assertEquals(1, retrieved.size)
        assertEquals("alt-1", retrieved[0].id)
    }

    @Test
    fun cacheClearsForUser() {
        val cache = InMemoryGuardianCache()
        cache.saveInsights("user-1", listOf(HealthInsight("i1", "T", "S", "active")))
        cache.clear("user-1")
        assertTrue(cache.getInsights("user-1").isEmpty())
    }
}
