# Documentation Index

The documentation is organized by decision type so product claims, engineering contracts, research evidence, and team workflow do not get mixed together. The root `README.md` is the concise GitHub landing page; this directory contains the authoritative details.

## Product and requirements

| Document | Purpose |
|---|---|
| [Product Requirements Document](product/PRD.md) | MVP users, value, scope, exclusions, non-diagnostic guardrails, and success criteria |
| [Software Requirements Specification](requirements/SRS.md) | Functional/non-functional requirements, contracts, constraints, and acceptance criteria |
| [Project blueprint](project/PROJECT_BLUEPRINT.md) | Long-form multi-member architecture and product vision |
| [Team ownership](project/TEAM_OWNERSHIP.md) | Canonical current module ownership, shared files, branches, and handoffs |

## Development and architecture

| Document | Purpose |
|---|---|
| [Development setup](development/SETUP.md) | Python, Android, backend, Docker, verification, and troubleshooting |
| [Git workflow](development/GIT_WORKFLOW.md) | Feature branches, safe synchronization, selective staging, PR flow, and protection recommendations |
| [Member 2 plan](development/MEMBER2_PLAN.md) | Implemented Sensor Intelligence scope, contracts, release gates, and pending hardware evidence |
| [Member 2 architecture](architecture/MEMBER2_ARCHITECTURE.md) | Runtime trust boundaries, data flow, fusion semantics, and Member 1/3 handoffs |
| [Future-ready Member 2 architecture](architecture/MEMBER2_FUTURE_READY_ARCHITECTURE.md) | Governed v3 observations, consent, capability trust, staged sync, abstention, and promotion gates |
| [Member 2 API](api/MEMBER2_API.md) | Authenticated production routes and development preview contracts |

## Privacy, security, and research

| Document | Purpose |
|---|---|
| [Data lifecycle](privacy/DATA_LIFECYCLE.md) | Consent, collection, minimization, retention, deletion, and user control |
| [Member 2 governance](governance/MEMBER2_GOVERNANCE.md) | Machine-enforced claim, consent, device-validation, model and evidence authority |
| [Threat model](security/MEMBER2_THREAT_MODEL.md) | Sensor/backend threats, mitigations, and integration dependencies |
| [Research basis](research/MEMBER2_RESEARCH.md) | Signal-processing decisions, authoritative sources, promotion criteria, and scientific limitations |
| [Dataset register](research/MEMBER2_DATASETS.md) | Approved sources, licenses/terms, fingerprints, acquisition, and governance |
| [PPG quality model card](research/PPG_QUALITY_MODEL_CARD.md) | Intended use, features, evaluation, exclusions, and known limitations |

## Verification evidence

| Document | Purpose |
|---|---|
| [Real-data protocol](testing/MEMBER2_REAL_DATA_PROTOCOL.md) | Participant-held-out and external validation methodology |
| [Real-data results](testing/MEMBER2_REAL_DATA_RESULTS.md) | Aggregate/participant evidence, rejected promotion gates, and interpretation |
| [Device matrix](testing/MEMBER2_DEVICE_MATRIX.md) | Required emulator, OEM, Health Connect provider, wearable, and camera evidence |

## Canonical Member 2 boundary

Member 2 owns consent-aware collection, source identity, timestamp/unit/provenance preservation, normalization, quality gates, deletion/reconciliation, non-diagnostic fusion, ingestion, and real-signal research. It does **not** own personalized baseline meaning (Member 1), diagnostic inference, emergency decisions, or Guardian explanations/safety policy (Member 3).

PPG quality research uses registered real datasets with participant-disjoint evaluation. Respiratory-rate and paired optical experiments remain explicitly limited by the recorded evidence; SpO₂ is not estimated without verified red/infrared mapping and device calibration. Raw datasets and local reports stay outside Git.
