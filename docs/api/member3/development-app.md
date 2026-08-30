# Member 3 Standalone Development App

`app.api.member3.app:create_member3_app` assembles every Member 3 router with
one shared set of in-memory services. It exists for development, demonstrations,
OpenAPI inspection, and integration tests. It does not modify or replace the
team's shared `app.main`.

## Run locally

From `backend/`, with the project dependencies installed:

```bash
uvicorn app.api.member3.app:create_member3_app --factory --reload
```

Then open `/docs` for the Member 3-only OpenAPI interface.

## Safety disclosures

The health endpoint reports that persistence is in-memory and external
connectors are disabled. The app never sends SMS/push messages or calls
emergency services.

## Integration value

All routers share the same service instances, so records created by the
Guardian orchestration endpoint are visible through the insights, alerts,
notifications, and emergency history APIs. Separate app instances do not share
state.
