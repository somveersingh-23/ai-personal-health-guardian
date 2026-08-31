# Member 2 Data Lifecycle

1. The user grants individual Health Connect read permissions. Background/history access is requested separately and only when the related feature is enabled.
2. Android maps supported records in memory. Camera frames remain on-device and are closed immediately after quality measurements.
3. For v3 live data, the client resolves the current consent receipt and purpose version immediately before upload. The bearer token and server user identity are never part of the observation body.
4. The backend checks receipt ownership/status/expiry/source/metric/purpose, validates source fidelity, derives a quality vector and atomically inserts/updates normalized records. Audit rows contain only a payload fingerprint and counts.
5. Member 1/3 receive minimized derived contracts with provenance, quality, contradiction and explicit missingness/abstention.
6. Health Connect deletions propagate by source ID. A value-free tombstone is written before the measurement row is removed. Expired-token reconciliation streams arbitrary-sized 30-day snapshots through a staged, explicit-completion protocol.
7. Pause stops collection/background work; revoke is managed in Health Connect and detected on the next permission/read check.
8. Consent withdrawal prevents further v3 ingestion under that receipt and can delete all linked Member 2 observations. Product-wide export/account deletion and backup expiry remain shared release gates.

## Offline research-data boundary

Authoritative public research datasets follow a separate offline path: approved registry -> local Git-ignored `data/` directory -> checksum/licence manifest -> feature extraction -> aggregate benchmark report. Raw waveforms, participant pickles/EDFs and participant-level outputs do not enter the production mobile sync, production database, ordinary logs, Git history or CI artifacts. Contract-conversion tests use deterministic dataset-relative timestamps and `source="research_dataset"`; they must never be presented as a logged-in user's live clinical history.

Before any pilot or store release, the product owner must define retention duration by data class, implement authenticated user export/account deletion across all three modules, publish the reviewed privacy policy, document backup deletion timing and complete the applicable Play/DPDP compliance review. A `retention_class` is an enforcement hook, not a made-up retention duration; these product/legal decisions cannot be invented in Member 2 code.
