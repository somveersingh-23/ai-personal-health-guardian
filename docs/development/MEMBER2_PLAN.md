# Member 2 Development and Model Plan

## Architecture

```text
Health Connect / approved connector / simulator
  -> capability + consent check
  -> v3 consent/purpose + observed capability check
  -> incremental sync (upsert + delete + tombstone + dedupe via source identity)
  -> minimized raw audit metadata
  -> typed mapper (instant / interval / series / session)
  -> integrity + provenance + sampled-signal + freshness + coverage + wear/motion quality vector
  -> normalized HealthEvent
  -> Member 1 baseline
  -> Member 2 quality-weighted fusion (isolated provenance)
  -> Member 3 safety rules and explanation
```

## Best model approach

### MVP v0 — deterministic and auditable

- Schema, unit, timestamp, provenance, clock-skew, and freshness checks.
- Health Connect metadata (`data_origin_package`, `source_record_type`, `source_last_modified_at`) and capability-aware missingness.
- Quality-weighted aggregation; no learned medical risk score.
- Camera quality only: exposure, blur, motion, placement and frame stability.
- Least privilege: permission states default to `unavailable`.

The repository has no labelled longitudinal dataset, reference-device ground truth, demographic coverage or clinical protocol. A trained health classifier now would be unverifiable.

### Research v1 — real-data implementation

- Raw PPG/ECG usability classifier using labelled clean/corrupted windows.
- Motion features aligned with IMU.
- Participant-level train/validation/test split.
- Metrics: sensitivity/specificity, AUROC/AUPRC, calibration, subgroup error and abstention coverage.

Implemented in `ml/sensor_intelligence`: approved-source registry, safe resumable acquisition, BIDMC/PPG-DaLiA/Sleep-EDF adapters, motion-aware PPG features, participant-disjoint evaluation, transparent logistic quality gate, production-contract validation and non-executable JSON model export. Full-dataset reports remain local evidence and do not create a medical claim.

### Camera/rPPG gate

- Simultaneous reference sensor; predefined lighting/motion protocol; device and skin-tone coverage; consent and ethics approval where applicable.
- Report MAE, limits of agreement, failure/abstention rate and subgroup performance.
- Never expose a measurement when frame quality is insufficient.

## Delivery phases

1. Contract gate: table ownership, IDs, units, deletion semantics, auth identity, composite unique constraint, and versioning.
2. Foundation: schemas/models, simulator, quality policy, fusion contract, and tests.
3. Persistence: shared DB/session, migrations, uniqueness, transactional ingestion and authorization.
4. API: device, scalar/batch ingestion, sync state, quality/fusion and OpenAPI tests.
5. Android foundation: native Activity UI, availability, least-privilege permissions, onboarding, rationale and manage-access UI.
6. Health Connect sync: typed mappers, separate change tokens, upserts/deletions and permission-aware WorkManager.
7. Quality/fusion: calibrated policies, missingness, provenance and versioned output.
8. Camera: CameraX user-initiated quality guidance; optional rPPG research flag.
9. Hardening: retention/deletion, threat model, observability, battery/device matrix and end-to-end demo.

## Implemented status (verified 2026-08-30)

- Backend contract, deterministic quality/fusion services, simulator, authenticated API, async persistence, migration, Docker image/Compose and CI are implemented.
- Governed Observation Envelope v3 is implemented without removing v2 migration compatibility. V3 carries consent/purpose, UCUM/LOINC hints, client/source provenance, acquisition context, quality vector, retention class and lifecycle metadata.
- Immutable consent receipts, withdrawal deletion cascade, value-free source tombstones and stale-replay protection are implemented.
- Device capability declarations are implemented with an anti-escalation boundary: clients can record experimental/unverified observations but cannot self-certify support, blocking, calibration or validation evidence.
- Quality-aware late fusion v3 reports selected sources, missing quality dimensions, cross-source contradiction and explicit abstention. Simulated input cannot produce Guardian evidence.
- The isolated Docker runtime smoke test passes on Docker Desktop 4.88.1 / Engine 29.7.2: PostgreSQL 16.10 became healthy, Alembic reached `0002_member2` with ten application tables, `/healthz` returned `ok`, and an authenticated PostgreSQL flow verified claim boundaries, v3 consent, UCUM/LOINC-normalized ingestion, consent withdrawal and linked-data deletion. All smoke-test containers, network and volume were removed.
- Health Connect typed mappers, feature/permission checks, Android-Keystore-only encrypted per-record-type tokens, upsert/deletion flow, permission-aware WorkManager scheduling, pause/resume and in-app permission revocation are implemented. Expired-token snapshots now stream page-by-page through resumable server sessions with no 5,000-record cutoff.
- CameraX prototype evaluates capture conditions only and never persists/transmits a frame or returns a physiological estimate.
- Member 1 handoff is `MultimodalFeatureVector` plus baseline-deviation input; Member 3 handoff is `MultimodalEvidenceVector`. Both now carry abstention semantics; neither output is a diagnosis or emergency action.
- Local verification passes: backend Ruff/bytecode checks plus 51 tests at 80.11% coverage (80% gate); Android AGP 9.3/pinned Gradle 9.5/JDK 17 compilation, 32 JVM tests and lint with zero issues. Android tests include the official AndroidX Health Connect fake, pagination, permission loss, unlink cleanup, streamed token-expiry reconciliation, governed v3 mapping and authenticated-encryption tamper checks.
- The real-signal research harness passes 32 ML/security unit tests at 58.49% coverage (55% gate), authoritative local acquisition, checksum verification and BIDMC/PPG-DaLiA/Sleep-EDF/CapnoBase/PTT-PPG validation. Reports include participant-level and participant-macro summaries, overlap disclosures, external respiration validation, paired-optical quality validation and explicit abstention boundaries. Results and promotion decisions are recorded in `docs/testing/MEMBER2_REAL_DATA_RESULTS.md`; raw data and participant-level output stay Git-ignored.

## Remaining release gates (not code-complete claims)

- Run the configured GitHub CI after push and add instrumented/emulator plus real-device evidence; the local Android compile/unit/lint gate passes, but hardware behavior cannot be established by a desktop build.
- Validate on the documented Android/OEM/wearable matrix, including revocation during sync, token expiry, process death, battery use and large-history behavior. Automated tests cover these policies, but cannot establish OEM/device behavior.
- Replace the placeholder in-app privacy rationale with the project owner's reviewed public policy and complete the Google Play Health apps declaration.
- Member 3/shared application startup must call `Member2Runtime.configureGovernedBackend(baseUrl, tokenProvider, governanceProvider)` after renewable authentication and active-consent sources are ready. V2 configuration remains migration-only; never store a bearer token or consent receipt in WorkManager input.
- A trusted signed/admin device-validation registry is deliberately not fabricated. Until physical evidence and authority exist, declarations remain experimental and cannot become medical-grade through the public API.
- Obtain team sign-off on `health_events` ownership and migration order before merging into `develop`.
- No rPPG/medical accuracy claim is permitted without the research protocol below.

## Definition of done

- Member 2 tests pass alone and in the integrated backend.
- Shared Member 1 boot fix and all Member 1/3 contracts reviewed before merge.
- No secret, raw image/video/waveform or health payload in Git/logs.
- Contract, privacy flow, threat model and device capability matrix documented.
- Claims limited to tested record types/devices; unavailable signals degrade gracefully.
