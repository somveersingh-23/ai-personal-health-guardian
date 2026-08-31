package com.healthguardian.sensor.healthconnect

import androidx.health.connect.client.changes.DeletionChange
import androidx.health.connect.client.changes.UpsertionChange
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.RestingHeartRateRecord
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.response.ChangesResponse
import java.time.Instant
import java.time.ZoneOffset
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class HealthConnectSyncEngineTest {
    private lateinit var fakeClient: FakeHealthConnectClient
    private lateinit var tokenStorage: InMemoryTokenStorage
    private lateinit var tokenStore: SyncTokenStore
    private lateinit var fakeBackend: FakeSensorBackend
    private lateinit var syncEngine: HealthConnectSyncEngine

    private val testPackage = "com.healthguardian.sensor"
    private val externalPackage = "com.samsung.shealth"

    @Before
    fun setUp() {
        fakeClient = FakeHealthConnectClient()
        tokenStorage = InMemoryTokenStorage()
        tokenStore = SyncTokenStore(tokenStorage, TestSyncTokenCipher())
        fakeBackend = FakeSensorBackend()

        syncEngine = HealthConnectSyncEngine(
            applicationPackage = testPackage,
            client = fakeClient,
            tokenStore = tokenStore,
            backend = fakeBackend,
        )
    }

    private fun grantAllSupported() {
        val perms = HealthConnectAccess.supportedRecordTypes(fakeClient).map {
            HealthPermission.getReadPermission(it)
        }.toSet()
        fakeClient.fakePermissions.grantedPermissions = perms
    }

    @Test
    fun missingPermissionSkipsRecordTypeAndClearsStoredToken() = runBlocking {
        tokenStore.save("HeartRateRecord", "stored_hr_token_v1", Instant.now())
        assertNotNull(tokenStore.load("HeartRateRecord"))

        // Only grant StepsRecord, not HeartRateRecord
        fakeClient.fakePermissions.grantedPermissions = setOf(
            HealthPermission.getReadPermission(StepsRecord::class),
        )

        val summary = syncEngine.syncAll()

        assertTrue(summary.revokedTypes.contains("HeartRateRecord"))
        assertNull(tokenStore.load("HeartRateRecord"))
    }

    @Test
    fun separateRecordTypesUseSeparateTokens() = runBlocking {
        grantAllSupported()

        fakeClient.tokenGenerator = { types ->
            "token_for_${types.first().simpleName}"
        }

        syncEngine.syncAll()

        val hrState = tokenStore.load("HeartRateRecord")
        val stepsState = tokenStore.load("StepsRecord")

        assertNotNull(hrState)
        assertNotNull(stepsState)
        assertEquals("token_for_HeartRateRecord", hrState?.token)
        assertEquals("token_for_StepsRecord", stepsState?.token)
    }

    @Test
    fun upsertAndDeletionChangesReachTheBackend() = runBlocking {
        grantAllSupported()
        tokenStore.save("StepsRecord", "initial_steps_token", Instant.now())

        val record = StepsRecord(
            startTime = Instant.parse("2026-08-29T08:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T09:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            count = 1200,
            metadata = createTestMetadata("steps_001", externalPackage),
        )

        fakeClient.changesResponses["initial_steps_token"] = ChangesResponse(
            changes = listOf(
                UpsertionChange(record),
                DeletionChange("steps_old_99"),
            ),
            nextChangesToken = "next_steps_token",
            hasMore = false,
            changesTokenExpired = false,
        )

        val summary = syncEngine.syncAll()

        val stepsDeletion = fakeBackend.deletedRequests.firstOrNull { it.first == "StepsRecord" }
        assertNotNull(stepsDeletion)
        assertEquals(listOf("steps_old_99"), stepsDeletion?.second)
        assertEquals("next_steps_token", tokenStore.load("StepsRecord")?.token)
    }

    @Test
    fun backendFailureDoesNotAdvanceToken() = runBlocking {
        grantAllSupported()
        tokenStore.save("StepsRecord", "initial_steps_token", Instant.now())

        val record = StepsRecord(
            startTime = Instant.parse("2026-08-29T08:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T09:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            count = 1200,
            metadata = createTestMetadata("steps_001", externalPackage),
        )

        fakeClient.changesResponses["initial_steps_token"] = ChangesResponse(
            changes = listOf(UpsertionChange(record)),
            nextChangesToken = "should_not_save_token",
            hasMore = false,
            changesTokenExpired = false,
        )

        fakeBackend.shouldFailUpload = true

        try {
            syncEngine.syncAll()
        } catch (_: IllegalStateException) {
            // Expected
        }

        // Token must remain the initial one!
        assertEquals("initial_steps_token", tokenStore.load("StepsRecord")?.token)
    }

    @Test
    fun multipleChangePagesAreProcessed() = runBlocking {
        grantAllSupported()
        tokenStore.save("StepsRecord", "page_1_token", Instant.now())

        val rec1 = StepsRecord(
            startTime = Instant.parse("2026-08-29T08:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T09:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            count = 500,
            metadata = createTestMetadata("steps_page_1", externalPackage),
        )
        val rec2 = StepsRecord(
            startTime = Instant.parse("2026-08-29T09:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T10:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            count = 700,
            metadata = createTestMetadata("steps_page_2", externalPackage),
        )

        fakeClient.changesResponses["page_1_token"] = ChangesResponse(
            changes = listOf(UpsertionChange(rec1)),
            nextChangesToken = "page_2_token",
            hasMore = true,
            changesTokenExpired = false,
        )
        fakeClient.changesResponses["page_2_token"] = ChangesResponse(
            changes = listOf(UpsertionChange(rec2)),
            nextChangesToken = "page_final_token",
            hasMore = false,
            changesTokenExpired = false,
        )

        val summary = syncEngine.syncAll()

        assertEquals("page_final_token", tokenStore.load("StepsRecord")?.token)
    }

    @Test
    fun expiredTokenTriggersBoundedFullSnapshotAndReconciles() = runBlocking {
        grantAllSupported()
        tokenStore.save("StepsRecord", "expired_token", Instant.now())

        fakeClient.changesResponses["expired_token"] = ChangesResponse(
            changes = emptyList(),
            nextChangesToken = "",
            hasMore = false,
            changesTokenExpired = true,
        )

        fakeClient.tokenGenerator = { "new_snapshot_token" }
        val snapshotRec = StepsRecord(
            startTime = Instant.parse("2026-08-29T08:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T09:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            count = 1000,
            metadata = createTestMetadata("rec_snap_01", externalPackage),
        )
        fakeClient.readRecordsMap[StepsRecord::class] = listOf(snapshotRec)

        val summary = syncEngine.syncAll()

        val stepsReconcile = fakeBackend.reconciledRequests.firstOrNull { it.sourceRecordType == "StepsRecord" }
        assertNotNull(stepsReconcile)
        assertEquals(listOf("rec_snap_01"), stepsReconcile?.authoritativeIds)
        assertEquals("new_snapshot_token", tokenStore.load("StepsRecord")?.token)
    }

    @Test
    fun selfOriginRecordsAreFilteredOut() = runBlocking {
        grantAllSupported()
        tokenStore.save("StepsRecord", "steps_token", Instant.now())

        val externalRec = StepsRecord(
            startTime = Instant.parse("2026-08-29T08:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T09:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            count = 500,
            metadata = createTestMetadata("ext_01", externalPackage),
        )
        val selfRec = StepsRecord(
            startTime = Instant.parse("2026-08-29T08:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T09:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            count = 500,
            metadata = createTestMetadata("self_01", testPackage), // Self-origin!
        )

        fakeClient.changesResponses["steps_token"] = ChangesResponse(
            changes = listOf(UpsertionChange(externalRec), UpsertionChange(selfRec)),
            nextChangesToken = "steps_token_next",
            hasMore = false,
            changesTokenExpired = false,
        )

        val summary = syncEngine.syncAll()

        val uploadedStepBatches = fakeBackend.uploadedBatches.flatten().filter { it.metric == "steps" }
        assertEquals(1, uploadedStepBatches.size)
        assertEquals(externalPackage, uploadedStepBatches[0].provenance.dataOriginPackage)
    }

    @Test
    fun securityExceptionDuringSyncHandledAsRevocation() = runBlocking {
        grantAllSupported()
        tokenStore.save("StepsRecord", "steps_token", Instant.now())
        fakeClient.throwSecurityExceptionOnSync = true

        val summary = syncEngine.syncAll()

        assertTrue(summary.revokedTypes.contains("StepsRecord"))
        assertNull(tokenStore.load("StepsRecord"))
    }

    @Test
    fun fullSnapshotReadsEveryRecordPage() = runBlocking {
        grantAllSupported()
        val record = StepsRecord(
            startTime = Instant.parse("2026-08-29T08:00:00Z"),
            startZoneOffset = ZoneOffset.UTC,
            endTime = Instant.parse("2026-08-29T09:00:00Z"),
            endZoneOffset = ZoneOffset.UTC,
            count = 100,
            metadata = createTestMetadata("paged-step", externalPackage),
        )
        fakeClient.readRecordsMap[StepsRecord::class] = List(501) { record }

        val summary = syncEngine.syncAll()

        assertEquals(501, summary.results.single { it.recordType == "StepsRecord" }.upserted)
        assertTrue(fakeClient.readRecordsRequestCount > HealthConnectAccess.supportedRecordTypes(fakeClient).size)
    }

    @Test
    fun largeReconciliationStreamsAllPagesAndSavesToken() = runBlocking {
        grantAllSupported()
        fakeClient.readRecordsMap[StepsRecord::class] =
            List(5_001) { index ->
                StepsRecord(
                    startTime = Instant.parse("2026-08-29T08:00:00Z"),
                    startZoneOffset = ZoneOffset.UTC,
                    endTime = Instant.parse("2026-08-29T09:00:00Z"),
                    endZoneOffset = ZoneOffset.UTC,
                    count = 100,
                    metadata = createTestMetadata("oversized-step-$index", externalPackage),
                )
            }

        val summary = syncEngine.syncAll()

        assertEquals(5_001, summary.results.single { it.recordType == "StepsRecord" }.upserted)
        assertEquals(5_001, fakeBackend.reconciledRequests
            .single { it.sourceRecordType == "StepsRecord" }
            .authoritativeIds.size)
        assertNotNull(tokenStore.load("StepsRecord"))
        assertTrue(fakeBackend.uploadedBatches.count { it.firstOrNull()?.metric == "steps" } > 1)
    }
}
