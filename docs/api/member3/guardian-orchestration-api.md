# Member 3 Guardian Orchestration API

`POST /api/v1/member3/guardian/process` connects the isolated Member 3 modules:

```text
structured evidence
  -> deterministic safety engine
  -> structured insight
  -> alert evaluation
  -> consent-aware notification intent
  -> emergency workflow (emergency_escalation only)
```

The orchestrator never changes the safety action, never invents evidence, and
never claims an external notification or emergency call occurred. Processing
is idempotent per user and event.

## Integration boundary

Member 1/2 should provide structured evidence, deviation score, confidence,
signal quality, and validated critical flags through the documented request.
They do not need to import Member 3 services.

## Current limitations

All repositories are in-memory. Authentication, persistent transactions,
cross-process idempotency, and external connectors require coordinated shared
infrastructure.

## Shared router registration

```python
from app.api.member3.guardian import router as member3_guardian_router

app.include_router(member3_guardian_router)
```
