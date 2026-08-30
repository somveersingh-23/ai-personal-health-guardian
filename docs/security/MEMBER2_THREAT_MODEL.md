# Member 2 Threat Model

| Threat | Control in this branch | Residual/release gate |
|---|---|---|
| Client claims another user | JWT `sub` is the only production identity; payload has no `user_id` | Member 3 identity provider/key rotation integration |
| Replay/duplicate sync | Stable source identity, event ID and last-modified conflict handling | Load and multi-device conflict tests |
| Deleted value resurrected by stale page | Value-free tombstone plus source last-modified comparison | Verify source-specific delete/recreate behavior on OEMs |
| Cross-user source collision | Unique source identity includes user; cross-user event-ID collision is rejected | PostgreSQL CI must stay required |
| Oversized/hostile payload | 1 MiB request limit, bounded lists/metadata, finite values, per-process rate backstop | Add distributed gateway rate limiting in deployment |
| Health data in logs | Audit stores hash/count only; network errors omit payload/token | Central logging review and redaction test |
| Token theft at rest | Health Connect change tokens use Android Keystore AES-GCM; bearer token is injected, not Worker input | Member 3 must provide short-lived token refresh and device-compromise policy |
| Network interception | Android cleartext disabled; backend adapter requires `https://` | Production certificate/pinning decision and rotation runbook |
| Permission revoked mid-sync | Preflight plus `SecurityException` handling; per-type token cleared | OEM/device instrumentation test |
| Token expiry causes stale data | Token reserved before snapshot; page-streamed staged reconciliation; token advances after completion | Large real-history/process-death device test |
| Change token exposed by backend | Android keeps AES-GCM token locally; optional server checkpoint accepts/stores/returns a client-computed SHA-256 fingerprint only | Remove legacy checkpoint after connector migration |
| User self-certifies a device | Public capability endpoint permits experimental/unverified declarations only | Signed/admin trusted registry and evidence review |
| Consent replay or purpose drift | Immutable receipt UUID; server checks subject/status/expiry/source/metric/purpose/version per v3 batch | Product-wide consent UI, notice archive and backup deletion |
| Camera privacy leak | User-initiated Activity, luma analysis in memory, every frame closed, no upload/storage | Static/dynamic privacy verification |
| False medical claim | Non-diagnostic names/descriptions; no trained disease/rPPG model | UI/content and Member 3 safety review |
| Research model artefact replaced | Non-executable JSON plus checked-in SHA-256 manifest and diagnostic-intended-use rejection | Signed artefact registry and rollback drill before activation |
| Secret committed | `.env` ignored; `.env.example` placeholders; Compose requires explicit secrets | Repository secret scanning and rotation process |

The in-process rate limiter is a safety backstop, not a distributed production control. Deploy behind an authenticated gateway/WAF with per-user quotas and trusted proxy configuration.
