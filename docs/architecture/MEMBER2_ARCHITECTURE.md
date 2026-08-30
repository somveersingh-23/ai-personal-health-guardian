# Member 2 Architecture and Handoff Contract

## Trust boundaries

```text
Health Connect / approved connector / simulator
  -> Android permission + capability + active-consent gate
  -> typed source mapper
  -> authenticated HTTPS boundary
  -> strict versioned Pydantic contract
  -> server-derived quality vector + capability confidence
  -> atomic idempotent persistence + value-free tombstones
  -> metric-aware, quality-weighted window aggregation
  -> Member 1 baseline deviation
  -> contradiction-aware, non-diagnostic evidence for Member 3
```

The Android client is untrusted. It may provide observations, acquisition context and source provenance, but it cannot provide `user_id`, server quality decisions, validation results or evidence strength. A public client also cannot promote its device to supported/calibrated status. The JWT subject is the production identity. Preview endpoints are disabled in production.

## Temporal model

| Shape | Metrics | Aggregation |
|---|---|---|
| Instant | resting HR, HRV RMSSD, SpO2, respiratory rate | arithmetic mean of accepted records |
| Interval | steps, active calories | sum after selecting one source group to prevent mirrored-source double counting |
| Series | heart rate, skin-temperature delta | sample mean with record/sample counts and coverage |
| Session | sleep | union of sleeping-stage intervals; awake/out-of-bed are excluded |

Missing metrics stay in `missing_metrics`; they are never converted to zero or silently imputed.

## Synchronization invariants

- One Android-Keystore-encrypted changes token per Health Connect record type; the optional backend checkpoint accepts only a client-computed fingerprint and never receives/returns a raw token.
- Reserve a token before the initial/expired-token 30-day snapshot so concurrent changes replay later.
- Process upserts and deletions before advancing the token.
- `(user_id, data_origin_package, source_record_type, source_record_id)` is unique when the source ID is present.
- A newer `source_last_modified_at` updates an existing record; equal/older replays are duplicates.
- Expired-token snapshots use a server reconciliation session. Android uploads each Health Connect page and appends authoritative IDs in chunks of at most 500.
- The server tombstones stale rows only after an explicit `complete_snapshot=true`; it never infers completeness from a missing page or network failure.
- Session/chunk retries are idempotent, histories are not held fully in Android memory, and the new change token advances only after session completion succeeds.
- `POST /sync/reconcile` remains a bounded v2 compatibility endpoint; new clients use the staged session protocol.

## Quality semantics

- `record_integrity_*`: schema, provenance, freshness context and transparent plausibility guardrails.
- `quality_vector`: provenance, freshness, coverage, wear, motion, signal and device-validation dimensions. Unmeasured dimensions remain null rather than being treated as perfect.
- `signal_quality_*`: only derived when waveform samples/capture measurements exist; otherwise `unknown`.
- Camera output: exposure/contrast/blur/motion/clipping guidance only. It is not PPG, heart rate, SpO2 or diagnosis.
- Fusion abstains when usable modalities or composite quality are insufficient and reports cross-source contradictions rather than hiding them in an average.
- `MultimodalEvidenceVector`: strength of baseline-deviation evidence, not medical risk probability.

## Governance and claim boundary

- Live v3 Health Connect/BLE/camera ingestion requires an immutable, active, purpose/version-specific consent receipt.
- Withdrawal can delete linked observations and leaves only value-free tombstones for stale-replay protection.
- Canonical UCUM units and conservative LOINC hints support later interoperability; this module does not claim a complete FHIR/ABDM export without shared patient identity and profile validation.
- Phone-camera SpO2 and unvalidated PPG respiration are prohibited claims. A model artifact cannot be enabled merely because it exists; checksum, intended use, external validation, device evidence and rollback gates remain mandatory.

## Member handoffs

Member 1 consumes `HealthEventResponse` or `MultimodalFeatureVector` and returns per-metric `BaselineDeviation` values. Member 2 combines those values with data quality into `MultimodalEvidenceVector`. Member 3 consumes the evidence vector and owns safety policy, user explanation and escalation. Member 3 must not reinterpret `evidence_strength` as disease probability.
