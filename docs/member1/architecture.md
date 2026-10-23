# Member 1 — Personal Health Digital Twin Architecture

## Scope
Member 1 owns health profile/event storage, the health-event timeline, preprocessing, personal statistical baselines, anomaly scoring, Digital Twin state snapshots, and data-driven insight artifacts. This implementation does not modify the AI/RAG module or teammates' sensor/guardian features.

## Data flow

```text
Synthetic or recorded health events
              |
              v
     Raw event CSV files
              |
              v
     Cleaning + features
              |
              +----------------------+
              |                      |
              v                      v
  Normal processed events   Deviation-test events
              |                      |
              v                      |
    Personal baselines               |
              |                      |
              +----------+-----------+
                         v
              Statistical anomaly scoring
                         |
                         v
              Per-user Digital Twin JSON/CSV
                         |
                         v
              Personalized insight JSON/CSV
                         |
                         v
          FastAPI read-only artifact endpoints
                         |
                         v
              Android Digital Twin screen
```

## API/database
PostgreSQL is accessed with SQLAlchemy `AsyncSession` and `asyncpg`. `health_profiles` stores user-level profile data; `health_events` stores timestamped measurements. The API serves CRUD events and chronological timelines. The health-intelligence endpoints read already-generated ML artifacts rather than running ML jobs in a web request.

## Important limitations
- User IDs are development identifiers. The endpoints do not yet authenticate a user or enforce record ownership. Do not deploy publicly until auth/authorization is integrated.
- Statistical deviation is not a diagnosis or a validated clinical threshold.
- `Base.metadata.create_all()` is for the current prototype; introduce Alembic migrations before production.
- The provided Docker credentials are local-development values and must be changed outside local development.
