# Member 3 Safety API

`POST /api/v1/member3/safety/evaluate` exposes the deterministic safety engine
through a validated HTTP contract. It accepts upstream deviation, confidence,
signal quality, evidence, validated critical flags, and explicit severe-symptom
confirmation.

The endpoint does not use an LLM, diagnose a condition, or modify evidence.
It returns one of: `normal`, `observe`, `re_measure`, `self_care`,
`caregiver_alert`, or `emergency_escalation`.
