# Member 2 — Multimodal Sensor Intelligence audit

Date: 2026-09-07
Scope: Member 2 only; no Member 1 source files were changed by this cleanup.

## Verified implementation

The implementation follows the original assignment's Health Connect-first architecture: Android reads supported Health Connect records, maps them to a provenance-preserving `HealthEvent`, sends bounded batches to the Member 2 API, and stores them in PostgreSQL through explicit Member 2 migrations.

Supported Health Connect inputs are heart rate, resting heart rate, HRV RMSSD, steps, active calories, sleep sessions/stages, skin-temperature delta, respiratory rate, and oxygen saturation **only when a permitted source device supplies them**. Every record preserves source package, record type and ID, source revision time, device context, time-zone offsets, recording method, and available quality context. Unknown quality is represented as unknown; it is never silently converted to a healthy value.

The Android sync engine keeps separate encrypted change tokens by record type, clears tokens after a permission loss, preserves upload/delete order, advances a token only after its page is accepted remotely, handles expired tokens with bounded snapshot reconciliation, and pauses/drains work before a profile switch or disconnect. The HTTP client permits HTTPS origins, with a narrow emulator/local-development HTTP exception, rejects unsafe origin components, and does not follow redirects.

The backend provides profile-bound local routes under `/api/v1/member2`, validates schemas and provenance, enforces idempotency and immutable source identity, prevents stale deletion/reconciliation from removing newer source revisions, serializes PostgreSQL writes per profile, supports explicit collection pause/purge/resume, and returns a non-diagnostic fusion vector. The production factory requires PostgreSQL and migration revision `0003_member2`; it does not create or alter Member 1 tables.

## Important bounds and safety decisions

- This is wellness/research software, not diagnosis, emergency detection, or medical-device software.
- The application does not estimate SpO2 from camera/PPG. Numeric SpO2 is accepted only when supplied by a source device.
- PPG respiration estimation did not meet the project validation standard and remains absent.
- The frozen PPG quality model is deliberately `disabled_in_production`. On the held-out Wrist Exercise check it accepted only 22 of 3,320 overlapping windows and the accepted-window pulse-rate MAE was about 27 bpm. This is insufficient evidence to activate it.
- Camera code is frame-quality research support only (for example blur/glare), not a medical measurement.
- A series is accepted only up to 10,000 samples and a session up to 500 stages. Larger source records need a designed streaming/segmentation protocol; they are rejected rather than silently truncated.
- Local export is a live keyset page of active normalized observations. It is not a complete legal-data export or a transaction snapshot.

## Verification completed locally

- Backend Member 2 suite: `19 passed, 4 skipped` on the local SQLite contract harness; the skips are PostgreSQL-only tests.
- Isolated PostgreSQL migration/runtime/concurrency suite previously passed: 4 tests. It uses a temporary `m2_audit_*` database and does not modify the team database.
- Android: `testDebugUnitTest` and `lintDebug` previously completed successfully (38 unit tests at the latest Android verification).
- ML: 39 unit tests passed using a clean Python 3.12 environment. The external Wrist Exercise report is generated locally, not committed.

## Required M1 integration (do not infer health conclusions)

1. Obtain the existing local `user_id` from the Member 1 health profile before configuring Member 2. Do not create a second profile identity.
2. Configure the explicit Member 2 API origin, then show permission, sync-in-progress, failed-record-type, and disconnected states in the UI.
3. Treat missing, rejected, unknown-quality, and incomplete data as unavailable—not normal/healthy. Keep temperature delta distinct from absolute temperature and request Health Connect aggregation for exact activity totals.
4. On disconnect, call the Member 2 runtime disconnect flow before leaving the screen. It drains active sync, clears local cursors, cancels work, and opens Health Connect settings without deleting server history.
5. Purge is destructive and pauses collection. Expose it only behind explicit user confirmation; resume must also be explicit and should configure a fresh sync state.

## Remaining release gates

Hardware/device validation is intentionally deferred: run the permission, background-work, process-death, disconnect/reconnect, and source-provenance flows on real Android devices and watches before release. Before a shared deployment, the team must also decide the service topology, HTTPS origin, database backup/restore, retention policy, operational monitoring, and how the Member 1 backend hosts or proxies the Member 2 router. No authentication is included because the current project decision is a local single-user build; do not expose these routes publicly without an approved access-control design.

## Primary references used

- [Android Health Connect: Sync data](https://developer.android.com/health-and-fitness/health-connect/sync-data)
- [Android guidance: Unsafe URI loading](https://developer.android.com/privacy-and-security/risks/unsafe-uri-loading)
- [PostgreSQL explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html)
- [SQLAlchemy session basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [Alembic autogenerate review guidance](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- [PhysioNet Wrist PPG During Exercise dataset](https://physionet.org/content/wrist/1.0.0/)
