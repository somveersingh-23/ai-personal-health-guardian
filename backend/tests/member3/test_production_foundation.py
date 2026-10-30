import asyncio
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from app.api.member3.app import build_service_container
from app.api.member3.production import create_production_member3_app
from app.models.member3.guardian_record import Member3Base, Member3GuardianRecord
from app.schemas.member3.alerts import AlertEvaluationResponse, AlertPriority, AlertRecord, AlertStatus
from app.schemas.member3.caregivers import CaregiverLink, CaregiverLinkStatus
from app.schemas.member3.conversations import ConversationRecord, ConversationTurn
from app.schemas.member3.emergency import EmergencyState, EmergencyWorkflowRecord
from app.schemas.member3.guardian import GuardianProcessResponse, SafetyDecisionTrace
from app.schemas.member3.insights import InsightCreateRequest, InsightRecord, InsightSeverity, InsightStatus
from app.schemas.member3.notifications import NotificationChannel, NotificationRecord, NotificationStatus
from app.services.member3.guardian.alert_service import _StoredAlert
from app.services.member3.guardian.insight_service import InsightService
from app.services.member3.persistence.container import build_persistent_container, create_member3_engine
from app.services.member3.persistence.repositories import (
    SqlAlertRepository,
    SqlCaregiverRepository,
    SqlConversationRepository,
    SqlEmergencyRepository,
    SqlGuardianOrchestrationRepository,
    SqlInsightRepository,
    SqlNotificationRepository,
)
from ml.safety import SafetyAction


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


def test_production_app_accepts_shared_m1_m2_jwt_contract(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    now = datetime.now(timezone.utc)
    token = jwt.encode({
        "sub": "42", "iat": now, "nbf": now, "exp": now + timedelta(minutes=5),
        "aud": "health-guardian-api", "iss": "ai-personal-health-guardian",
    }, SECRET, algorithm="HS256")
    app = create_production_member3_app(
        database_url="sqlite+pysqlite:///:memory:", create_schema=True
    )

    response = TestClient(app).get(
        "/api/v1/member3/insights?user_id=42",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == "42"


def test_all_7_repositories_support_sync_and_async_sessions(tmp_path):
    sync_engine = create_engine("sqlite+pysqlite:///:memory:")
    Member3Base.metadata.create_all(sync_engine)
    sm = sessionmaker(sync_engine, expire_on_commit=False)

    db_path = tmp_path / "test_async_repo.db"
    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async def init_async_schema():
        async with async_engine.begin() as conn:
            await conn.run_sync(Member3Base.metadata.create_all)

    asyncio.run(init_async_schema())
    asm = async_sessionmaker(async_engine, expire_on_commit=False)

    now = datetime.now(timezone.utc)

    for idx, session_source in enumerate([sm, asm, sync_engine, async_engine]):
        u = f"user-{idx}"
        e = f"evt-{idx}"

        r_insight = SqlInsightRepository(session_source)
        r_alert = SqlAlertRepository(session_source)
        r_notif = SqlNotificationRepository(session_source)
        r_caregiver = SqlCaregiverRepository(session_source)
        r_emerg = SqlEmergencyRepository(session_source)
        r_conv = SqlConversationRepository(session_source)
        r_orch = SqlGuardianOrchestrationRepository(session_source)

        # 1. Insight
        ins = InsightRecord(
            insight_id=f"ins-{idx}", user_id=u, source_event_id=e, insight_type="recovery",
            safety_action=SafetyAction.OBSERVE, severity=InsightSeverity.LOW, status=InsightStatus.NEW,
            title="Title", summary="Sum", evidence=(), limitations=(), disclaimer="Disc",
            created_at=now, updated_at=now,
        )
        r_insight.save(ins)
        assert r_insight.get(f"ins-{idx}") is not None
        assert r_insight.get_by_source(u, e) is not None
        assert len(r_insight.list_for_user(u)) == 1

        # 2. Alert
        alt = AlertRecord(
            alert_id=f"alt-{idx}", user_id=u, event_id=e, safety_action=SafetyAction.CAREGIVER_ALERT,
            priority=AlertPriority.HIGH, status=AlertStatus.ACTIVE, title="Title", message="Msg",
            evidence=["ev1"], requires_human_confirmation=True, created_at=now, updated_at=now,
        )
        r_alert.save(_StoredAlert(alt, f"fp{idx}"))
        assert r_alert.get(f"alt-{idx}") is not None
        assert r_alert.get_by_event(u, e) is not None
        assert len(r_alert.list_for_user(u)) == 1

        # 3. Notification
        notif = NotificationRecord(
            notification_id=f"notif-{idx}", user_id=u, source_event_id=e, title="Title", body="Body",
            priority=AlertPriority.LOW, channel=NotificationChannel.IN_APP, target_ref=None,
            status=NotificationStatus.DELIVERED, attempt_count=1, provider_receipt_id="rec-1",
            failure_reason=None, created_at=now, updated_at=now,
        )
        r_notif.save(notif)
        assert r_notif.get(f"notif-{idx}") is not None
        assert r_notif.get_by_source(u, e, NotificationChannel.IN_APP) is not None
        assert len(r_notif.list_for_user(u)) == 1

        # 4. Caregiver
        cg = CaregiverLink(
            link_id=f"cg-{idx}", user_id=u, caregiver_user_ref=f"cg_ref_{idx}", relationship_label="family",
            status=CaregiverLinkStatus.PENDING, created_at=now, updated_at=now,
        )
        r_caregiver.save(cg)
        assert r_caregiver.get(f"cg-{idx}") is not None
        assert r_caregiver.get_by_pair(u, f"cg_ref_{idx}") is not None
        assert len(r_caregiver.list_for_user(u)) == 1

        # 5. Emergency
        em = EmergencyWorkflowRecord(
            workflow_id=f"em-{idx}", user_id=u, alert_id=f"alt-{idx}", state=EmergencyState.AWAITING_CONFIRMATION,
            safety_action=SafetyAction.EMERGENCY_ESCALATION, safety_reason="Severe symptoms",
            evidence=("heart_rate",), caregiver_contact_id=None, urgent_instruction="urgent",
            audit_events=(), external_action_performed=False, created_at=now, updated_at=now,
        )
        r_emerg.save(em)
        assert r_emerg.get(f"em-{idx}") is not None
        assert r_emerg.get_by_alert(u, f"alt-{idx}") is not None
        assert len(r_emerg.list_for_user(u)) == 1

        # 6. Conversation
        turn = ConversationTurn(
            message_id=f"m-{idx}", question="Q", answer="A", safety_action=SafetyAction.OBSERVE,
            evidence_metrics=("heart_rate",), disclaimer="Disclaimer", created_at=now,
        )
        conv = ConversationRecord(
            conversation_id=f"conv-{idx}", user_id=u, title="T", turns=(turn,), created_at=now, updated_at=now,
        )
        r_conv.save(conv)
        assert r_conv.get(f"conv-{idx}") is not None
        assert r_conv.get_by_message(u, f"m-{idx}") is not None
        assert len(r_conv.list_for_user(u)) == 1

        # 7. Orchestration
        trace = SafetyDecisionTrace(
            decision_id=f"dec-{idx}", policy_version="1.0", source_event_id=e, evaluated_at=now,
            action=SafetyAction.OBSERVE, reason="Small deviation", requires_human_confirmation=False,
            evidence_metrics=("heart_rate",), evidence_count=1, critical_flags_count=0,
            deviation_score=0.5, confidence=0.9, signal_quality=0.9, user_confirmed_severe_symptoms=False,
        )
        orch = GuardianProcessResponse(
            event_id=e, user_id=u, safety_action=SafetyAction.OBSERVE, safety_reason="Observed",
            decision_trace=trace, insight=ins, alert=AlertEvaluationResponse(created=False, suppressed_reason="No alert"),
            notifications=None, emergency_workflow=None, processed_at=now,
        )
        r_orch.save(orch)
        assert r_orch.get(u, e) is not None
        assert len(r_orch.list_for_user(u)) == 1

        # Deletions
        assert r_insight.delete_for_user(u) == 1
        assert r_alert.delete_for_user(u) == 1
        assert r_notif.delete_for_user(u) == 1
        assert r_caregiver.delete_for_user(u) == 1
        assert r_emerg.delete_for_user(u) == 1
        assert r_conv.delete_for_user(u) == 1
        assert r_orch.delete_for_user(u) == 1


def test_shared_main_app_lifespan_creates_tables_and_persists(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMBER3_JWT_SECRET", SECRET)
    db_file = tmp_path / "shared_health.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    from app.database import database as db_mod
    if hasattr(db_mod, 'configure_database'):
        db_mod.configure_database(db_url)
    else:
        from sqlalchemy.ext.asyncio import create_async_engine
        test_engine = create_async_engine(db_url)
        monkeypatch.setattr(db_mod, 'engine', test_engine)

    from app.main import app
    target_engine = getattr(db_mod, 'engine', None)
    app.state.member3_services = build_persistent_container(target_engine)

    token = _token("shared-user")
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # Check that lifespan created both Base (health_profiles) and Member3Base (member3_guardian_records)
        sync_eng = create_engine(f"sqlite:///{db_file}")
        insp = inspect(sync_eng)
        table_names = insp.get_table_names()
        assert "health_profiles" in table_names
        assert "member3_guardian_records" in table_names

        # Verify persistent store through endpoint
        create_res = client.post(
            "/api/v1/member3/insights",
            json={
                "user_id": "shared-user",
                "source_event_id": "event-shared-1",
                "insight_type": "recovery",
                "safety_action": "observe",
                "safety_reason": "Stable test reading",
                "evidence": [{
                    "metric": "sleep",
                    "current_value": 7.5,
                    "baseline_value": 7.0,
                    "unit": "hours",
                    "direction": "within normal",
                    "confidence": 0.95,
                    "signal_quality": 0.9,
                }],
            },
            headers=headers,
        )
        assert create_res.status_code == 200

        # Query directly from database to verify persistence in member3_guardian_records
        with sessionmaker(sync_eng)() as session:
            rows = session.scalars(
                select(Member3GuardianRecord).where(
                    Member3GuardianRecord.record_type == "insight",
                    Member3GuardianRecord.user_id == "shared-user",
                )
            ).all()
            assert len(rows) == 1
            assert rows[0].secondary_key == "event-shared-1"


def test_fallback_to_in_memory_container():
    container = build_service_container()
    assert container.insights is not None
    assert container.alerts is not None
    assert container.guardian is not None
