# Member 2 Data and Claim Governance

## Machine-enforced boundaries

- `GET /api/v1/member2/claims` exposes feature claim class, evidence status, prohibited claims and promotion requirements.
- Live v3 observations require a matching active consent receipt.
- Consent receipts are immutable; a reused UUID with changed terms is rejected.
- Withdrawal stops future v3 ingestion under that receipt and can delete linked observations.
- Deletion tombstones contain source identity and reason but no measurement values.
- Clients can declare an observed device capability only as experimental/unverified. Trusted validation cannot be self-asserted.
- Learned model artefacts are non-executable JSON, checksum pinned and explicitly disabled in production.

## Human-controlled release gates

Code cannot invent the public privacy notice, retention duration, clinical intended use, representative study population or regulatory classification. Owners must approve these items before a release and record the decision/version in the repository or deployment evidence system.

## Evidence handling

Device evidence uses `docs/testing/member2-device-evidence.example.json` as the schema example and `scripts/validate-member2-device-evidence.py` as the privacy guard. Evidence records contain operational counts/timing only. Raw health values, bearer/change tokens, camera frames, waveforms and participant identifiers are forbidden.

Research data remains under ignored local `data/` paths. Aggregate reports may be committed only after privacy, licence and re-identification review.

## Promotion authority

| Change | Required authority |
|---|---|
| Observed device/record type | Authenticated user/app declaration |
| Supported or blocked device profile | Trusted server/admin registry plus validation evidence |
| Research model activation | Research owner, frozen evaluation and safety review |
| Wellness claim | Product/privacy/store-policy review |
| Clinical claim | Clinical, quality, legal/regulatory and safety approval |
