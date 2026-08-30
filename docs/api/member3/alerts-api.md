# Member 3 Alert API

The alert system consumes an upstream `SafetyAction`; it does not calculate
risk or diagnose conditions. `normal` and `observe` are suppressed. Other
actions map to low, medium, high, or critical alerts.

## Endpoints

- `POST /api/v1/member3/alerts/evaluate`
- `GET /api/v1/member3/alerts?user_id=...`
- `PATCH /api/v1/member3/alerts/{alert_id}/status`

Evaluation is idempotent by `event_id`. Equivalent active alerts for the same
user are suppressed during a 30-minute cooldown. Critical alerts cannot be
dismissed; they must be acknowledged or resolved.

## Development limitation

The current repository is intentionally in-memory and loses data on process
restart. A persistent Member 3 alert repository and audit table will be added
as a separate database feature after the team agrees on shared migrations.

## Shared integration step

Do not edit `main.py` concurrently. During integration, add:

```python
from app.api.member3.alerts import router as member3_alerts_router

app.include_router(member3_alerts_router)
```

## Test

```bash
python -m pytest backend/tests/member3 -v
```
