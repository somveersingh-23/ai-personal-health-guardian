# Member 3 Notification API

This module records notification intents and delivery receipts. It does not
send push messages or SMS and never marks a notification delivered without an
explicit provider receipt.

## Safety and privacy

- Requested channels must appear in `consented_channels`; critical priority
  does not override consent.
- Push/SMS require an opaque target reference. Raw phone numbers and tokens
  should not be placed in requests or logs.
- Creation is idempotent per user, source event, and channel.
- Failed deliveries may retry up to three dispatch attempts.

## Endpoints

- `POST /api/v1/member3/notifications`
- `GET /api/v1/member3/notifications?user_id=...`
- `POST /api/v1/member3/notifications/{id}/dispatch`
- `POST /api/v1/member3/notifications/{id}/receipt`
- `POST /api/v1/member3/notifications/{id}/retry`
- `POST /api/v1/member3/notifications/{id}/cancel`

## Development limitations

Storage is in-memory. Authentication, persistent delivery logs, encrypted
target resolution, push/SMS connectors, and signed provider callbacks require
separate coordinated integration.

## Shared integration step

```python
from app.api.member3.notifications import router as member3_notifications_router

app.include_router(member3_notifications_router)
```
