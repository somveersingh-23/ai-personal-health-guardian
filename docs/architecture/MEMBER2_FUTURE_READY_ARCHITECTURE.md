# Member 2 Future-Ready Architecture

Status: implemented engineering contract, with physical-device and clinical promotion gates explicitly open.

## Intended use

Member 2 creates trustworthy, source-faithful sensor observations and non-diagnostic evidence. It does not diagnose disease, detect emergencies, or convert consumer-device data into a medical-device claim. Personalized interpretation belongs to Member 1; Guardian reasoning and safety policy belong to Member 3.

## Trust pipeline

```text
Health Connect / approved BLE / research adapter / simulator
  -> feature availability and permission check
  -> active consent receipt and purpose-version check (v3 live data)
  -> paged upsert/delete sync with encrypted local cursors
  -> staged, resumable expired-token reconciliation
  -> source-faithful HealthEvent + UCUM/LOINC export hints
  -> record integrity + provenance + freshness + coverage + wear/motion quality vector
  -> observed device-capability policy; no client self-certification
  -> source-aware temporal alignment and late fusion
  -> explicit contradiction, missingness and abstention
  -> minimized M1 feature and M3 evidence contracts
```

## Observation Envelope v3

V3 extends, rather than silently mutates, the v2 connector contract. A live sensor observation carries:

- temporal shape: instant, interval, series or session;
- source and canonical UCUM units;
- approved LOINC hint where the metric is unambiguous;
- source app, source record ID/type, last-modified time and optional client record version;
- device profile ID, manufacturer/model/type, body site and sampling rate when available;
- original timezone offsets, wear state and motion state;
- consent receipt, purpose/version, retention class and mapper version;
- a multidimensional quality vector and lifecycle metadata.

`null` means a quality dimension was not measured. It must never be rewritten as zero or silently treated as perfect quality.

## Device trust

The authenticated user endpoint records observed capabilities only. It cannot mark a device `supported`, `blocked`, calibrated, or validated. Trusted promotion requires an administrator-controlled or signed registry backed by a versioned physical-device protocol. Until then, an observed capability is `experimental` and contributes limited confidence.

The Android mapper creates a privacy-safe device-profile UUID from source package plus manufacturer/model/type. This identifies a source profile, not a unique physical person or hardware serial number.

## Consent and deletion

V3 Health Connect, BLE and camera-derived observations require an active immutable consent receipt whose subject, source, metric, purpose and purpose version match the upload. Withdrawal can delete linked observations. Source deletions and reconciliation create value-free tombstones before measurement rows are removed, preventing stale replay without retaining the deleted health value.

## Sync invariants

1. A separate Android-Keystore-encrypted cursor is maintained per record type.
2. A cursor advances only after every upsert/deletion operation for that page succeeds.
3. Token expiry reserves a new change token before the snapshot starts.
4. Snapshot pages are uploaded and reconciled incrementally; there is no 5,000-record memory/abort limit.
5. Server reconciliation is idempotent, session-scoped, chunked and finalized only with explicit `complete_snapshot=true`.
6. A stale upsert at or before a source tombstone is ignored; a genuinely newer source revision may re-create the observation.
7. Actual Health Connect change tokens remain encrypted on Android. The optional server checkpoint accepts, stores and returns only a client-computed SHA-256 fingerprint; the raw token never crosses this API.

## Quality and fusion

Quality dimensions are record integrity, provenance, freshness, coverage, signal SQI, wear confidence, motion artefact, calibration and device-validation confidence. The fusion engine uses metric-specific temporal semantics and conservative quality weighting. It reports selected sources, missing dimensions, contradictions, missing metrics and abstention reasons.

Simulated data and rejected/blocked observations cannot produce Guardian evidence. A feature vector below configured evidence/quality requirements returns an explicit abstention instead of a fabricated score.

## Signal claim policy

| Signal/feature | Current policy |
|---|---|
| Health Connect HR, HRV, activity, sleep, temperature, vendor SpO2/RR | Preserve as sourced observations; no ECG/clinical-equivalence claim |
| PPG quality classifier | Research only; exact JSON artefact checksum-pinned and disabled in production |
| PPG-derived respiration | Rejected experiment; no production output |
| Phone-camera SpO2 | Prohibited; paired optical wavelengths, calibration and clinical evidence are absent |
| Camera module | In-memory exposure/blur/motion/clipping quality only |
| BLE | Future connector must use adopted Bluetooth SIG profiles and a reviewed device allow-list |

## Interoperability boundary

The internal envelope remains optimized for source fidelity. FHIR is an export boundary, not the internal database schema. A later ABDM integration must profile FHIR R4 Observation/Provenance, map patient identity through the shared identity service, and validate every code/unit against the target implementation guide. Health Connect Personal Health Record APIs remain outside the MVP until their experimental/policy boundary is reviewed.

## Promotion gates

- Engineering gate: migrations, API contract, idempotency, deletion, reconciliation, unit/lint/coverage and Docker PostgreSQL checks.
- Device gate: recorded Android/OEM/wearable/camera evidence passes the device matrix.
- Wellness gate: privacy notice, Play Health declaration, retention/export/account deletion and security review are complete.
- Research gate: approved prospective protocol, representative cohorts, device-disjoint frozen evaluation and subgroup reporting.
- Clinical gate: intended-use analysis, scientific/analytical/clinical validation, quality system, risk management and applicable regulatory review.

## Primary references

- Android: <https://developer.android.com/health-and-fitness/health-connect/sync-data>
- Health Connect data model: <https://developer.android.com/health-and-fitness/health-connect/data-format>
- Health Connect metadata: <https://developer.android.com/health-and-fitness/health-connect/metadata>
- HL7 FHIR R4 Observation: <https://hl7.org/fhir/R4/observation.html>
- UCUM: <https://ucum.org/ucum>
- ABDM FHIR implementation guide: <https://www.nrces.in/preview/ndhm/fhir/r4/index.html>
- IMDRF clinical evaluation: <https://www.imdrf.org/documents/software-medical-device-samd-clinical-evaluation>
- FDA/IMDRF GMLP: <https://www.fda.gov/medical-devices/software-medical-device-samd/good-machine-learning-practice-medical-device-development-guiding-principles>
- OWASP MASVS: <https://mas.owasp.org/MASVS/>
- NIST SSDF: <https://csrc.nist.gov/pubs/sp/800/218/final>
