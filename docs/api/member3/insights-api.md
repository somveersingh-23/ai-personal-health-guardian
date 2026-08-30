# Member 3 Health Insights API

This API converts a precomputed safety decision and supplied structured
evidence into a display-ready insight. It does not calculate risk, diagnose a
condition, or change the incoming `SafetyAction`.

## Endpoints

- `POST /api/v1/member3/insights`
- `GET /api/v1/member3/insights?user_id=...`
- `GET /api/v1/member3/insights/{insight_id}`
- `PATCH /api/v1/member3/insights/{insight_id}/status`

Insights support `new`, `viewed`, and `archived` lifecycle states. Creation is
idempotent per user and source event. Low confidence or signal quality is
surfaced as a limitation rather than hidden.

## Limitations

Storage is in-memory until the team agrees on shared SQLAlchemy dependencies,
database migrations, authentication, and retention rules.

## Shared integration

```python
from app.api.member3.insights import router as member3_insights_router

app.include_router(member3_insights_router)
```
