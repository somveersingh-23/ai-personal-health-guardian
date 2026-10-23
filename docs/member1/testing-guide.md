# Member 1 Testing Guide

## Backend tests
From the repository root:

```bash
cd backend
python -m pytest
```

The test fixture uses an in-memory SQLite database. Production/local PostgreSQL behavior still needs a separate integration run with PostgreSQL.

## ML tests
From the repository root:

```bash
python -m pytest ml/member1/tests
```

## Android unit tests/build — Windows CMD
```bat
cd mobile\android
gradlew.bat testDebugUnitTest
gradlew.bat assembleDebug
```

## Manual API smoke test
1. Start PostgreSQL and the FastAPI app.
2. Run the Member 1 ML pipeline from the repository root.
3. Open `/docs`.
4. Create a health event with `POST /api/v1/member1/health-events`.
5. List it with `GET /api/v1/member1/health-events?user_id=1`.
6. Retrieve `GET /api/member1/health-intelligence/1/digital-twin`.
7. Retrieve `GET /api/member1/health-intelligence/1/insights`.

## End-to-end scenarios
- Loading: API request is in progress; show a spinner.
- Success: a twin with current metrics is rendered.
- Empty: a valid response has no metric/event/baseline records.
- Error: backend is stopped or artifact is missing; show a useful message.
- Retry: start backend/generate artifacts, then tap retry.
- Invalid time window: timeline/event listing rejects start time later than end time.
- Data integrity: user A's event/twin is not mixed with user B's data in ML output.

Do not mark a test as passed until it has actually been run in the local environment.
