from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.api.member3.production import create_production_member3_app
from app.models.member3.guardian_record import Member3Base
from app.schemas.member3.insights import InsightCreateRequest
from app.services.member3.guardian.insight_service import InsightService
from app.services.member3.persistence.container import create_member3_engine
from app.services.member3.persistence.repositories import SqlInsightRepository
from sqlalchemy.orm import sessionmaker


SECRET = "member3-test-secret-that-is-at-least-32-bytes"


def _token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": user_id, "iat": now, "exp": now + timedelta(minutes=5),
        "aud": "health-guardian-mobile", "iss": "health-guardian",
    }, SECRET, algorithm="HS256")


def _insight_request() -> InsightCreateRequest:
    return InsightCreateRequest(
        user_id="user-a", source_event_id="event-1", insight_type="recovery",
        safety_action="observe", safety_reason="Small stable change",
        evidence=[{
            "metric": "heart_rate", "current_value": 82, "baseline_value": 76,
            "unit": "bpm", "direction": "elevated", "confidence": 0.9,
            "signal_quality": 0.95,
        }],
    )


def test_sql_repository_survives_service_recreation():
    engine = create_member3_engine("sqlite+pysqlite:///:memory:")
    Member3Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    created = InsightService(SqlInsightRepository(sessions)).create(_insight_request())
    restored = InsightService(SqlInsightRepository(sessions)).get(created.insight_id)
    assert restored == created


def test_production_app_requires_jwt_and_rejects_cross_user(monkeypatch):
    monkeypatch.setenv("MEMBER3_JWT_SECRET", SECRET)
    app = create_production_member3_app(database_url="sqlite+pysqlite:///:memory:", create_schema=True)
    client = TestClient(app)
    assert client.get("/api/v1/member3/insights?user_id=user-a").status_code == 401
    response = client.get(
        "/api/v1/member3/insights?user_id=user-b",
        headers={"Authorization": f"Bearer {_token('user-a')}"},
    )
    assert response.status_code == 403


def test_production_app_allows_owner(monkeypatch):
    monkeypatch.setenv("MEMBER3_JWT_SECRET", SECRET)
    app = create_production_member3_app(database_url="sqlite+pysqlite:///:memory:", create_schema=True)
    response = TestClient(app).get(
        "/api/v1/member3/insights?user_id=user-a",
        headers={"Authorization": f"Bearer {_token('user-a')}"},
    )
    assert response.status_code == 200
    assert response.json() == {"user_id": "user-a", "insights": [], "count": 0}
