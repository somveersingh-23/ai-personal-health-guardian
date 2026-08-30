# Multimodal Sensor Intelligence — Software Requirements Specification

## System boundary

Member 2 owns connectors, synchronization, normalization, sensor provenance, signal-quality assessment, non-diagnostic fusion, camera quality research, and module tests/docs. Member 1 owns personal baseline/anomaly interpretation. Member 3 owns safety actions and explanations.

## Functional requirements

- **M2-FR-001** Request only record-type permissions needed by enabled features and re-check permission before each read. Permissions default to `unavailable` under least privilege.
- **M2-FR-002** Show unavailable, denied, revoked, foreground-only, and background-enabled states plus pause/manage-access controls.
- **M2-FR-003** Store separate Android-Keystore-encrypted Health Connect change tokens per independently consumed record type, process upserts/deletions, ignore self-originated records, and recover from expired tokens using paged, staged reconciliation without holding the full history in memory.
- **M2-FR-004** Preserve full Health Connect provenance: `data_origin_package`, `source_record_type`, `source_record_id`, device metadata, recording method, observed time, `source_last_modified_at` when available, and ingestion time.
- **M2-FR-005** Enforce timezone-aware timestamps, finite values, canonical metric-unit pairs, bounded batches (max 500), clock-skew tolerances ($\le 60$s), and versioned schemas.
- **M2-FR-006** Reject malformed input; flag outside-supported-range readings without converting them into diagnoses. Separate record integrity/provenance (`record_integrity_score`), sampled-signal quality (`signal_quality_score`) and data age (`freshness_status`). Scalar plausibility alone must never be called signal quality.
- **M2-FR-007** Distinguish scalar, sampled-waveform, and camera quality. Do not run waveform algorithms without samples and sampling frequency.
- **M2-FR-008** Fusion operates on one user and declared window, lists missing metrics, uses quality weights, and isolates provenance to only actually contributing events.
- **M2-FR-009** Expose normalized HealthEvents to Member 1 and non-diagnostic fused evidence/quality/provenance to Member 3.
- **M2-FR-010** Label simulated feeds explicitly with `source="simulated"`, `recording_method="synthetic"`, and `permission_state="unavailable"`. Exclude them from pilot analysis by default.
- **M2-FR-011** Camera capture is user initiated and evaluates lighting, blur, motion, placement, capability and capture failure without diagnosis.
- **M2-FR-012** Permission withdrawal stops sync; source deletions propagate according to agreed retention policy.
- **M2-FR-013** Research datasets are versioned in an approved-source registry with licence, citation, checksum, byte limits, intended use and limitations. Raw data remains outside Git and application logs.
- **M2-FR-014** Dataset adapters emit `source="research_dataset"`, preserve dataset/participant provenance, and clearly label relative anchored time. Research data must never be represented as a user's live clinical measurement.
- **M2-FR-015** PPG quality training/evaluation splits by participant, fits preprocessing only on training data, selects thresholds only on validation data, and reports untouched test performance and abstention coverage.
- **M2-FR-016** SpO2 estimation requires an appropriately validated multi-wavelength raw optical source. A stored SpO2 reference value or single-channel PPG is insufficient.
- **M2-FR-017** Serialized research models use a non-executable, reviewable parameter format and carry intended-use, target-definition and version metadata.
- **M2-FR-018** Live v3 Health Connect, BLE and camera observations require an immutable active consent receipt matching authenticated subject, source, metric, purpose and purpose version.
- **M2-FR-019** Client capability declarations remain experimental/unverified. A client cannot self-assert supported/blocked status, calibration or validation evidence.
- **M2-FR-020** Expired-token reconciliation is session-scoped, chunked, retry-idempotent and finalized only after explicit `complete_snapshot=true`; an incomplete session cannot delete source records or advance the local token.
- **M2-FR-021** Quality is multidimensional: integrity, provenance, freshness, coverage, signal, wear, motion, calibration and device-validation evidence. Unmeasured dimensions remain null, never silently perfect.
- **M2-FR-022** Source deletion and consent-withdrawal deletion remove measurements while retaining value-free tombstones sufficient to block stale replay; a genuinely newer source revision may recreate an observation.
- **M2-FR-023** Machine-readable claim boundaries prohibit unsupported camera SpO2, diagnostic use and production PPG-derived respiration. Research model activation requires an exact artefact checksum, declared intended use and external/device evidence.

## Non-functional requirements

- **Security:** TLS; encrypted local storage; authorization from authenticated identity, never payload `user_id`; no secrets or raw health data in logs.
- **Privacy:** purpose limitation, minimization, versioned consent receipts, pause/revoke, export/delete, retention classes and auditable access. Product owners must define actual retention durations and backup-deletion policy before release.
- **Reliability:** idempotent ingestion via unique composite key `(user_id, data_origin_package, source_record_type, source_record_id)` and primary key `event_id`, transactional batches, retry/backoff, deletion reconciliation and observable sync cursors.
- **Performance:** max 500 events/request and 500 reconciliation IDs/chunk, bounded waveform payloads, page-streamed histories, expiring reconciliation sessions and battery-aware background work.
- **Explainability:** every quality result records policy/model version and contributing checks.
- **Safety:** outputs are informational evidence; no disease label or emergency decision originates here.
- **Testability:** deterministic simulator, synthetic unit fixtures, authoritative real-signal datasets, participant-disjoint evaluation, contract/integration tests and device matrix.

## Data contracts

The discriminated `ReadingCreate` union (instant, interval, series and session) is untrusted connector input. V2 remains a migration/research contract; v3 adds consent/purpose, acquisition context and richer provenance. `HealthEventCreate` is server-derived normalized output. Derived trust fields (`quality_vector`, quality decisions, validation status and evidence strength) must not be accepted from external clients. Health Connect input strictly requires `data_origin_package`, `source_record_type`, `source_record_id` and `source_last_modified_at` for exact identity and conflict resolution. Normalized observations retain source units and add canonical UCUM units plus conservative LOINC hints where unambiguous.

## Acceptance criteria

- Wrong unit, naive timestamp, NaN/infinity, empty/oversized batch, clock skew >60s, and cross-user fusion fail.
- Re-reading a source record is idempotent via composite unique constraint and deletion changes remove/tombstone derived data.
- Low confidence cannot be presented as reliable.
- Historical data (>24h) retains measurement validity while correctly exposing `freshness_status="historical"`.
- Backend tests cover authentication, v3 consent, capability anti-escalation, persistence, stale records, duplicate/update behavior, tombstone replay protection, staged reconciliation, contradictions and abstention. Android JVM/CI tests cover capture quality, governed typed mapping, AndroidX fake-client change pagination, read pagination, permission loss, unlink cleanup, authenticated token storage and page-streamed reconciliation beyond 5,000 records. Real permission UI, Android Keystore, WorkManager process lifecycle, OEM token expiry and wearable behavior remain instrumented/device-matrix release gates.
