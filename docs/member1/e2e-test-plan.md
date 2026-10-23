# Member 1 End-to-End Test Plan

## Preconditions
- PostgreSQL is reachable and `DATABASE_URL` is configured.
- FastAPI starts and `GET /health` returns `{"status":"ok"}`.
- The ML pipeline has produced per-user JSON/CSV artifacts.
- Android debug base URL points to the host API.

## Scenarios
1. **API health:** root and health endpoints return 200.
2. **Event CRUD:** create → list → retrieve → patch → delete an event.
3. **Timeline:** events appear newest-first; date filters and pagination work.
4. **ML reproducibility:** run `scripts/run_member1_ml_pipeline.py`; verify baseline, anomaly, twin, and insight artifacts exist.
5. **User isolation in artifacts:** inspect user-specific JSON; it contains only that user's events/metrics.
6. **Backend artifacts:** call the Digital Twin and insights endpoints for a generated user.
7. **Missing artifacts:** call for a user without artifacts and verify a clear 404 response.
8. **Android success:** with API and artifacts ready, the Digital Twin section renders current metrics.
9. **Android error/retry:** stop API, confirm an error state, restart API, and tap Retry.
10. **Docker:** `docker compose config`, `docker compose up --build -d`, `/health`, then `docker compose down`.

## Exit criteria
All automated tests pass, the debug APK assembles, all manual scenarios have a recorded result, no secret files are tracked, and no production-readiness claim is made until authentication and migrations exist.
