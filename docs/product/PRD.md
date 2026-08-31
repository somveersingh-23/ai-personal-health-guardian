# AI Personal Health Guardian — Product Requirements Document

## Product decision

The MVP is a consent-based Android research/wellness prototype, not a diagnostic or emergency medical device. It demonstrates a trustworthy loop: collect supported signals, preserve provenance, reject unusable inputs, learn a personal baseline, combine evidence, and explain changes without claiming disease.

## Users and jobs

- Primary user: an adult Android user who records health/fitness data through a supported wearable or Health Connect.
- Research operator: runs simulated and consented pilot data, audits quality and false alerts.
- Team developer: integrates one of three modules through stable versioned contracts.

Users need to connect a source, understand exactly what is collected, pause/revoke access, see data freshness/quality, and receive a cautious explanation of a meaningful change.

## MVP scope

1. Consent and Health Connect connection status.
2. Read available heart rate, resting heart rate, HRV RMSSD, sleep duration, steps, oxygen saturation, respiratory rate, skin temperature, and active calories. Availability is capability- and permission-dependent.
3. Sync using source record IDs, modification metadata, Android-Keystore-encrypted per-record-type change tokens, deletion tombstones, deduplication, and page-streamed staged recovery from token expiry.
4. Normalize instant, interval, series and session readings into versioned HealthEvents that retain source units/provenance and add canonical UCUM units plus conservative LOINC hints.
5. Require a purpose/version-specific consent receipt for live v3 collection and prevent clients from self-certifying device support or calibration.
6. Assign a transparent non-clinical quality vector across integrity, freshness, provenance, coverage, signal, wear/motion and device evidence; unknown evidence is never considered perfect.
7. Produce quality-weighted aligned features with explicit missingness, source contradictions and abstention; do not impute silently.
8. Feed normalized events to Member 1 and non-diagnostic fused evidence to Member 3; simulated input cannot create Guardian evidence.
9. Provide simulated data before real-device testing.
10. Camera milestone is capture guidance and frame quality only; camera SpO2 is prohibited and any rPPG experiment remains outside the production path.

## Explicit non-goals

- Diagnosis, treatment recommendation, medication decision, cancer/retinal screening, or guaranteed emergency detection.
- Secret microphone/camera capture, advertising use, insurer profiling, or sale of health data.
- Raw ECG/PPG availability through Health Connect; waveform processing only applies to a connector that supplies sampled data.
- Universal smartwatch/BLE support, OEM system integration, custom hardware, or clinical deployment in the MVP.

## Success metrics

- 100% of persisted events have schema version, source, source record ID when available, observation time, unit, permission state, and quality state.
- Duplicate re-sync creates zero duplicate normalized events.
- Revoked permissions stop collection and surface a user-readable state.
- Missing metrics appear as missing, never as zero.
- Simulated end-to-end pipeline passes automated tests with no cross-user fusion.
- Pilot metrics: sync success, stale-data rate, rejection/flag rate, alert false-positive rate, battery impact, and user trust; no accuracy claim before labelled reference-device validation.

## Release gates

- Contract signed off by all three members.
- Privacy notice, consent, deletion/export design, threat model, and data-retention policy approved.
- Health Connect permission declarations match actual features.
- No diagnostic language in UI/API output.
- Device and demographic validation plan approved before camera/rPPG claims.
- Physical Android/OEM/wearable evidence passes the privacy-safe device matrix; desktop tests cannot satisfy this gate.
- Research artefacts remain disabled until checksum, external validation, intended-use, rollback and approval gates are satisfied.
