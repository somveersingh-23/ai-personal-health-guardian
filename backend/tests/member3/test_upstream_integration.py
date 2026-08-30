from datetime import datetime, timezone

import pytest

from app.models.member3.guardian_record import Member3Base
from app.schemas.member3.upstream import BaselineResult, SensorIntelligenceResult
from app.services.member3.integration.upstream_adapter import UpstreamContractError, UpstreamGuardianAdapter
from app.services.member3.persistence.container import build_persistent_container, create_member3_engine


def _baseline(event_id="event-42"):
    return BaselineResult(
        user_id="user-a", event_id=event_id, metric="heart_rate", baseline=72,
        current=88, unit="bpm", deviation_score=2.1, status="above_normal",
        confidence=0.92, occurred_at=datetime.now(timezone.utc),
    )


def _sensors(event_id="event-42"):
    return SensorIntelligenceResult(event_id=event_id, signal_quality=0.95, fusion_confidence=0.89)


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
