from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from ai.rag.governance import audit_knowledge_base
from app.api.member3.production import create_production_member3_app


ROOT = Path(__file__).resolve().parents[3]
SECRET = "member3-test-secret-that-is-at-least-32-bytes"


def _token(user_id="user-a", *, expired=False):
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": user_id, "iat": now - timedelta(hours=2) if expired else now,
        "exp": now - timedelta(hours=1) if expired else now + timedelta(minutes=5),
        "aud": "health-guardian-mobile", "iss": "health-guardian",
    }, SECRET, algorithm="HS256")


def test_prototype_knowledge_base_is_not_misrepresented_as_clinically_reviewed():
    audit = audit_knowledge_base(ROOT / "ai" / "knowledge_base" / "member3" / "health_topics.jsonl")
    assert audit.total == 22
    assert not audit.production_ready
    assert all("clinical source/sign-off missing" in issue for issue in audit.issues)


def test_expired_and_tampered_tokens_are_rejected(monkeypatch):
    monkeypatch.setenv("MEMBER3_JWT_SECRET", SECRET)
    client = TestClient(create_production_member3_app(database_url="sqlite+pysqlite:///:memory:", create_schema=True))
    endpoint = "/api/v1/member3/insights?user_id=user-a"
    assert client.get(endpoint, headers={"Authorization": f"Bearer {_token(expired=True)}"}).status_code == 401
    assert client.get(endpoint, headers={"Authorization": f"Bearer {_token()}tampered"}).status_code == 401


def test_body_user_id_cannot_cross_token_boundary(monkeypatch):
    monkeypatch.setenv("MEMBER3_JWT_SECRET", SECRET)
    client = TestClient(create_production_member3_app(database_url="sqlite+pysqlite:///:memory:", create_schema=True))
    response = client.post(
        "/api/v1/member3/caregivers",
        headers={"Authorization": f"Bearer {_token('user-a')}"},
        json={"user_id": "user-b", "caregiver_user_ref": "caregiver-1", "relationship_label": "family"},
    )
    assert response.status_code == 403
