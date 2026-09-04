package com.healthguardian.sensor.healthconnect

import java.time.Instant
import java.util.Base64
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class SyncTokenStoreTest {
    private lateinit var storage: InMemoryTokenStorage
    private lateinit var store: SyncTokenStore

    @Before
    fun setUp() {
        storage = InMemoryTokenStorage()
        store = SyncTokenStore(storage, TestSyncTokenCipher())
    }

    @Test
    fun saveAndLoadRoundTripWithAADBinding() = runBlocking {
        val now = Instant.parse("2026-08-29T12:00:00Z")
        store.save("HeartRateRecord", "sample_sync_token_12345", now)

        val loaded = store.load("HeartRateRecord")
        assertNotNull(loaded)
        assertEquals("sample_sync_token_12345", loaded?.token)
        assertEquals(now.toEpochMilli(), loaded?.lastSuccessfulSyncAt?.toEpochMilli())
    }

    @Test
    fun clearRemovesOnlyTargetRecordType() = runBlocking {
        val now = Instant.now()
        store.save("HeartRateRecord", "hr_token", now)
        store.save("StepsRecord", "steps_token", now)

        store.clear("HeartRateRecord")

        assertNull(store.load("HeartRateRecord"))
        assertNotNull(store.load("StepsRecord"))
        assertEquals("steps_token", store.load("StepsRecord")?.token)
    }

    @Test
    fun clearAllRemovesAllTokens() = runBlocking {
        val now = Instant.now()
        store.save("HeartRateRecord", "hr_token", now)
        store.save("StepsRecord", "steps_token", now)
        store.save("SleepSessionRecord", "sleep_token", now)

        store.clearAll()

        assertNull(store.load("HeartRateRecord"))
        assertNull(store.load("StepsRecord"))
        assertNull(store.load("SleepSessionRecord"))
    }

    @Test
    fun pauseAndResumeState() = runBlocking {
        assertFalse(store.isPaused())

        store.setPaused(true)
        assertTrue(store.isPaused())

        store.setPaused(false)
        assertFalse(store.isPaused())
    }

    @Test
    fun cipherRejectsMismatchedAADAndTamperedCiphertext() = runBlocking {
        val cipher = TestSyncTokenCipher()
        val encrypted = cipher.encrypt("secret_token_val", "HeartRateRecord")

        // Decrypt with correct recordType -> succeeds
        val decrypted = cipher.decrypt(encrypted, "HeartRateRecord")
        assertEquals("secret_token_val", decrypted)

        // Decrypt with mismatched recordType -> AAD authentication fails -> throws or returns null via load()
        var failed = false
        try {
            cipher.decrypt(encrypted, "StepsRecord")
        } catch (_: Exception) {
            failed = true
        }
        assertTrue("Decryption with wrong AAD must fail authentication", failed)

        val tamperedBytes = Base64.getDecoder().decode(encrypted)
        tamperedBytes[tamperedBytes.lastIndex] = (tamperedBytes.last().toInt() xor 0x01).toByte()
        val tampered = Base64.getEncoder().encodeToString(tamperedBytes)
        failed = false
        try {
            cipher.decrypt(tampered, "HeartRateRecord")
        } catch (_: Exception) {
            failed = true
        }
        assertTrue("Ciphertext tampering must fail authentication", failed)
    }
}
