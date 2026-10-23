# Member 1 API Reference

The OpenAPI source of truth is `GET /openapi.json`; interactive requests are available at `/docs`.

## Health
- `GET /` — project status.
- `GET /health` — lightweight health check.

## Health profile
Base path: `/api/v1/member1/health-profile`
- `POST /api/v1/member1/health-profile` — create a profile.
- `GET /api/v1/member1/health-profile/{user_id}` — retrieve a profile by development user ID.

## Health events
Base path: `/api/v1/member1/health-events`
- `POST /api/v1/member1/health-events` — create an event.
- `GET /api/v1/member1/health-events?user_id=1` — list events; optional `event_type`, `start_time`, `end_time`, `limit`, `offset`.
- `GET /api/v1/member1/health-events/{event_id}` — retrieve one event.
- `PATCH /api/v1/member1/health-events/{event_id}` — update supplied fields.
- `DELETE /api/v1/member1/health-events/{event_id}` — delete one event (204).

Example event body:

```json
{
  "user_id": 1,
  "event_type": "heart_rate",
  "event_time": "2026-10-23T08:00:00Z",
  "value": 72,
  "unit": "bpm",
  "source": "manual",
  "notes": "Optional note",
  "metadata_json": {}
}
```

## Timeline
- `GET /api/v1/member1/health-timeline/{user_id}` — newest-first events; optional `start_time`, `end_time`, `limit`, `offset`.

## Health intelligence (ML artifacts must already exist)
- `GET /api/member1/health-intelligence/{user_id}/digital-twin`
- `GET /api/member1/health-intelligence/{user_id}/metrics`
- `GET /api/member1/health-intelligence/{user_id}/insights`
- `GET /api/member1/health-intelligence/{user_id}` — combined summary.

Missing generated artifacts return HTTP 404. Malformed artifacts return HTTP 503. The API does not automatically generate artifacts on a request.
