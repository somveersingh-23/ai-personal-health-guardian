# Android Sensor Intelligence

Native Android implementation for Member 2: Health Connect permission/sync handling, secure per-record change tokens, deletion and expired-token reconciliation, WorkManager scheduling, typed backend mapping, and a CameraX capture-quality research prototype.

## Toolchain

- JDK 17
- Gradle 9.5.0 via the committed, checksum-pinned wrapper
- Android Gradle Plugin 9.3.x
- compile/target SDK 37; minimum SDK 26

Run from `mobile/android`:

```powershell
.\gradlew.bat --no-daemon testDebugUnitTest lintDebug
```

On Linux/macOS use `./gradlew`. The wrapper JAR is committed so CI and contributors use the same verified Gradle distribution; do not replace it with an unreviewed binary.

## Integration boundary

Member 3/shared application startup configures authenticated upload only after its renewable session/token provider is ready:

```kotlin
Member2Runtime.configureGovernedBackend(
    baseUrl = "https://api.example.com",
    tokenProvider = { sessionRepository.freshAccessToken() },
    governanceProvider = {
        val consent = consentRepository.requireActiveSensorConsent()
        ObservationGovernance(
            consentReceiptId = consent.receiptId,
            purposeVersion = consent.purposeVersion,
        )
    },
)
```

The backend URL must use HTTPS. Do not store bearer tokens or consent receipts in WorkManager input. V3 resolves both at upload time so withdrawal/expiry is observed before another batch is sent. `configureAuthenticatedBackend` is retained for v2 migration/testing only.

If the user separately grants Health Connect background access, application startup may call `SensorSyncScheduler.enable(context)` from a coroutine. Logout or disconnect must call `SensorSyncScheduler.disable(context)` and `Member2Runtime.clear()`; the explicit disconnect flow also clears change tokens and opens Health Connect access settings.

## Release boundary

The demo Activity exposes availability, required/optional permissions, manual sync, pause, access management, rationale, disconnect, and camera capture-quality screens. Distribution still requires a real backend URL, identity-provider refresh integration, reviewed privacy policy/store disclosures, instrumented tests, and the physical OEM/wearable evidence in `docs/testing/MEMBER2_DEVICE_MATRIX.md`.

Expired-token snapshots are streamed page by page. The backend receives authoritative IDs through a staged reconciliation session; there is no 5,000-record in-memory cutoff. The new change token is persisted only after uploads and reconciliation completion succeed.

Camera processing currently evaluates capture quality; it is not a diagnostic camera measurement. SpO₂ is not produced without paired raw optical channels, verified wavelength mapping, device-specific calibration, and validation.
