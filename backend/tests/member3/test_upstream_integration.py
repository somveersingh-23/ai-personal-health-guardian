from datetime import datetime, timezone
import math
import pytest
from pydantic import ValidationError

from app.models.member3.guardian_record import Member3Base
from app.schemas.member3.upstream import BaselineResult, SensorIntelligenceResult
from app.services.member3.integration.upstream_adapter import UpstreamContractError, UpstreamGuardianAdapter
from app.services.member3.persistence.container import build_persistent_container, create_member3_engine


def _baseline(event_id="event-42", user_id="user-a", **kwargs):
    params = {
        "user_id": user_id, "event_id": event_id, "metric": "heart_rate", "baseline": 72,
        "current": 88, "unit": "bpm", "deviation_score": 2.1, "status": "above_normal",
        "confidence": 0.92, "occurred_at": datetime.now(timezone.utc),
    }
    params.update(kwargs)
    return BaselineResult(**params)


def _sensors(event_id="event-42", user_id="user-a", **kwargs):
    params = {"user_id": user_id, "event_id": event_id, "signal_quality": 0.95, "fusion_confidence": 0.89}
    params.update(kwargs)
    return SensorIntelligenceResult(**params)


def test_member1_and_member2_outputs_flow_through_guardian_to_database():
    engine = create_member3_engine("sqlite+pysqlite:///:memory:")
    Member3Base.metadata.create_all(engine)
    services = build_persistent_container(engine)
    request = UpstreamGuardianAdapter().build(_baseline(), _sensors())
    response = services.guardian.process(request)
    assert response.user_id == "user-a"
    assert response.insight.evidence[0].metric == "heart_rate"
    assert services.insights.list_insights("user-a").count == 1


def test_adapter_rejects_mismatched_upstream_events():
    with pytest.raises(UpstreamContractError, match="same event_id"):
        UpstreamGuardianAdapter().build(_baseline("event-1"), _sensors("event-2"))


def test_adapter_rejects_mismatched_user_id():
    with pytest.raises(UpstreamContractError, match="does not match sensor user_id"):
        UpstreamGuardianAdapter().build(_baseline(user_id="user-1"), _sensors(user_id="user-2"))


def test_upstream_schemas_reject_invalid_ranges():
    with pytest.raises(ValidationError):
        _baseline(confidence=1.5)

    with pytest.raises(ValidationError):
        _sensors(signal_quality=2.0)


def test_persistence_across_service_recreation():
    engine = create_member3_engine("sqlite+pysqlite:///:memory:")
    Member3Base.metadata.create_all(engine)

    # Instance 1 saves a record
    services1 = build_persistent_container(engine)
    req = UpstreamGuardianAdapter().build(_baseline(), _sensors())
    services1.guardian.process(req)
    assert services1.insights.list_insights("user-a").count == 1

    # Instance 2 reading the same engine
    services2 = build_persistent_container(engine)
    assert services2.insights.list_insights("user-a").count == 1
    assert services2.alerts.list_alerts("user-a").count == 1
