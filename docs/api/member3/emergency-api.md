# Member 3 Emergency Workflow API

This prototype records an emergency workflow after the deterministic safety
engine has already produced `emergency_escalation`. It does not diagnose risk,
place calls, send messages, or claim that an external action occurred.

Every workflow immediately returns this instruction: if there may be immediate
danger, call local emergency services now or ask someone nearby to call. The UI
must never make the user wait for confirmation before showing that instruction.

## Endpoints

- `POST /api/v1/member3/emergency/workflows`
- `GET /api/v1/member3/emergency/workflows/{workflow_id}`
- `GET /api/v1/member3/emergency/workflows?user_id=...`
- `POST /api/v1/member3/emergency/workflows/{workflow_id}/commands`

Commands: `confirm`, `record_caregiver_notification`,
`request_emergency_contact`, `cancel`, and `resolve`. Every accepted command is
appended to the workflow audit trail. “Notification recorded” means a caller
reported that action; this service does not send it.

## Development limitations

- In-memory storage is lost on restart.
- No SMS, phone, push-notification, or emergency-service connector exists.
- Actor identity is not authenticated until shared authentication integration.
- Production use requires persistent audit storage, authorization, consent,
  regional emergency-number handling, delivery receipts, and clinical review.

## Shared integration step

During coordinated integration only:

```python
from app.api.member3.emergency import router as member3_emergency_router

app.include_router(member3_emergency_router)
```
