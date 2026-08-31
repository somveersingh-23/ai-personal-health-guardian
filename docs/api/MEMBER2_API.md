# Member 2 API

Base path: `/api/v1/member2`. All production endpoints require `Authorization: Bearer <JWT>` and derive the user from the validated `sub` claim. Request/response details and enum values are authoritative in `/openapi.json`.

| Method and path | Purpose |
|---|---|
| `POST /events/batch` | Atomic ingestion of 1–500 typed readings |
| `GET /claims` | Machine-readable claim/evidence boundaries and promotion gates |
| `POST /consents` | Create an immutable purpose-specific consent receipt |
| `POST /consents/{receipt_id}/withdraw` | Withdraw consent and optionally delete linked observations |
| `POST /features/align` | Read persisted records and create a metric-aware feature vector |
| `POST /evidence/fuse` | Combine Member 1 deviations with quality; non-diagnostic |
| `POST /quality/record-integrity` | Assess untrusted record validity/provenance/freshness |
| `POST /quality/waveform` | Transparent sampled-waveform SQI |
| `POST /camera/quality` | Assess capture measurements; no image upload |
| `PUT /devices` | Upsert least-privilege device state |
| `PUT /devices/capabilities` | Record experimental/unverified observed capabilities; cannot self-certify validation |
| `PUT /sync/cursor` | Legacy managed-connector checkpoint; accepts/stores/returns only a lowercase SHA-256 fingerprint, never the raw token |
| `POST /sync/deletions` | Propagate explicit Health Connect deletion IDs |
| `POST /sync/reconcile` | Backward-compatible bounded reconciliation |
| `POST /sync/reconcile/sessions` | Begin a resumable large-history reconciliation |
| `POST /sync/reconcile/sessions/{id}/records` | Append up to 500 authoritative source IDs idempotently |
| `POST /sync/reconcile/sessions/{id}/complete` | Atomically tombstone stale records after explicit completion |

`/api/v1/member2/preview/*` accepts preview user IDs and simulated data only when `ENABLE_PREVIEW_ENDPOINTS=true`; production configuration rejects enabling it.

## Ingestion rules

- `temporal_type` discriminates instant, interval, series and session bodies.
- V2 remains accepted for migration. V3 live Health Connect/BLE/camera events require an active consent receipt and matching purpose version.
- Normalized events retain connector units and add canonical UCUM units plus approved LOINC hints where unambiguous.
- Health Connect requires origin package, record type, record ID and last-modified time.
- Timestamps must have a UTC offset. Future skew above 60 seconds fails.
- Batches are all-or-nothing at validation and database transaction boundaries.
- Duplicate count means an equal/older source replay; update count means a newer source revision.
- Deletions create value-free tombstones before health rows are removed. A stale replay cannot resurrect a deleted value.
- Quality is a vector. Unknown signal/device/calibration evidence is not converted into perfect quality.
- Feature/evidence output includes explicit missingness, contradiction and abstention fields.
- Raw health bodies, waveform arrays and camera frames are not placed in audit logs. Audit storage contains SHA-256, byte count, event count, user and source only.

## Local run

```powershell
cd backend
python -m pip install -r requirements-dev.txt
$env:PYTHONPATH='.'
python -m uvicorn app.main:app --reload
```

The built-in development secret is never valid deployment configuration. Production requires PostgreSQL, a unique JWT secret of at least 32 characters, migrations and preview/auto-create disabled.
