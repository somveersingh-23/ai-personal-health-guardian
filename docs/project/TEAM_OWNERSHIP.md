# Team Ownership and Integration Boundaries

This file is the canonical ownership map for the current three-member plan. Ownership identifies the primary reviewer and integration responsibility; it does not make another member's inherited files safe to delete.

## Branch model

```text
main
└── develop
    ├── feature/m1-health-digital-twin
    ├── feature/m2-sensor-intelligence
    └── feature/m3-ai-guardian
```

All feature branches start from `develop` and contain the full repository tree. Member 3 creates `feature/m3-ai-guardian` from current `develop` when that work begins; Member 2 should not create or populate it on Member 3's behalf.

## Primary ownership

| Owner | Capability | Primary paths and contracts |
|---|---|---|
| Member 1 | Personal Health Digital Twin: profile, personalized baseline, trend/deviation interpretation | `backend/app/api/member1/`, `backend/app/models/member1/`, `backend/app/schemas/member1/`, future baseline services and their tests |
| Member 2 | Multimodal Sensor Intelligence: collection, source identity, normalization, quality, fusion, ingestion and sensor research | `mobile/android/`, `ml/sensor_intelligence/`, `backend/app/**/member2/`, sensor services, Member 2 tests/research docs |
| Member 3 | AI Guardian: identity/session integration, explanation, safety policy and user-facing escalation boundaries | `ai/`, future Guardian endpoints/services/UI and their tests |

## Shared files

The following affect multiple owners and require cross-member review:

- `backend/app/main.py`, database base/session configuration, and Alembic migrations
- authentication/JWT contracts and Android application startup
- shared API schemas and versioned handoff contracts
- root `README.md`, `.env.example`, `docker-compose.yml`, CI workflows, and release configuration
- privacy language, intended-use claims, retention, deletion, and security policy

Do not silently redefine another member's response schema or database meaning. Prefer additive, versioned contracts and document the migration.

## Data handoffs

```text
Android observations
  -> Member 2 HealthEvent + quality/provenance
  -> MultimodalFeatureVector
  -> Member 1 BaselineDeviation per metric
  -> Member 2 MultimodalEvidenceVector
  -> Member 3 safety policy and explanation
```

- Member 1 consumes normalized events or `MultimodalFeatureVector`; it owns personalized baseline meaning.
- Member 2 combines Member 1's standardized deviations with quality and missingness. `combined_evidence_strength` is evidence quality/strength, not a disease probability.
- Member 3 consumes `MultimodalEvidenceVector`; it owns user explanation and safety behavior and must preserve uncertainty and provenance.
- Authentication identity comes from the verified JWT subject, never from a client-supplied `user_id`.

## Merge boundary

A member can change a shared file when required for their feature, but the pull request must identify the affected owners and explain compatibility. Integration happens feature branch → `develop`; stable, reviewed releases move `develop` → `main`.
