package com.healthguardian.sensor.healthconnect

import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.records.metadata.Device
import androidx.health.connect.client.records.metadata.Metadata
import androidx.health.connect.client.request.ChangesTokenRequest
import androidx.health.connect.client.testing.FakeHealthConnectClient as AndroidxFakeHealthConnectClient
import androidx.health.connect.client.testing.FakePermissionController
import java.time.Instant
import java.time.ZoneOffset
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test

class OfficialHealthConnectFakeTest {
    @Test
    fun officialFakeTracksAndPaginatesChangesEndToEnd() = runBlocking {
        val permissionController = FakePermissionController(grantAll = true)
        val client = AndroidxFakeHealthConnectClient(
            permissionController = permissionController,
        )
        client.setPackageName("com.samsung.shealth")
        client.pageSizeGetChanges = 2
        permissionController.grantPermissions(
            HealthConnectAccess.supportedRecordTypes(client).mapTo(mutableSetOf()) {
                HealthPermission.getReadPermission(it)
            },
        )
        val initialToken = client.getChangesToken(
            ChangesTokenRequest(setOf(StepsRecord::class)),
        )
        val device = Device(manufacturer = "Samsung", model = "Watch", type = Device.TYPE_WATCH)
        client.insertRecords(
            List(3) { index ->
                val start = Instant.parse("2026-08-29T08:00:00Z").plusSeconds(index * 3_600L)
                StepsRecord(
                    startTime = start,
                    startZoneOffset = ZoneOffset.UTC,
                    endTime = start.plusSeconds(3_600),
                    endZoneOffset = ZoneOffset.UTC,
                    count = 100L + index,
                    metadata = Metadata.autoRecorded(
                        device = device,
                        clientRecordId = "official-fake-$index",
                    ),
                )
            },
        )
        val store = SyncTokenStore(InMemoryTokenStorage(), TestSyncTokenCipher())
        store.save("StepsRecord", initialToken, Instant.now())
        val backend = FakeSensorBackend()
        val engine = HealthConnectSyncEngine(
            applicationPackage = "com.healthguardian.sensor",
            client = client,
            tokenStore = store,
            backend = backend,
        )

        val summary = engine.syncAll()

        assertEquals(3, summary.results.single { it.recordType == "StepsRecord" }.upserted)
        assertEquals(3, backend.uploadedBatches.flatten().count { it.metric == "steps" })
    }
}
