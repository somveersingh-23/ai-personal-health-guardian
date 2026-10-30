from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError

from app.models.member3.guardian_record import Member3Base
from app.schemas.member3.upstream import (
    BaselineResult,
    M2MultimodalEvidenceVector,
    SensorIntelligenceResult,
)
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


def _m2_vector(**overrides):
    start = datetime(2026, 9, 13, 9, 0, tzinfo=timezone.utc)
    payload = {
        "schema_version": "2.0.0",
        "user_id": 42,
        "window_start": start,
        "window_end": start + timedelta(minutes=5),
        "evidence": [
            {
                "metric": "heart_rate",
                "direction": "above",
                "standardized_deviation": 2.2,
                "evidence_weight": 0.91,
                "quality_weight": 0.88,
            }
        ],
        "combined_evidence_strength": 0.90,
        "missing_baselines": ["hrv_rmssd"],
        "abstained": False,
        "abstention_reasons": [],
        "non_diagnostic": True,
    }
    payload.update(overrides)
    return M2MultimodalEvidenceVector(**payload)


def test_exact_m2_evidence_vector_maps_without_fabricating_raw_measurements():
    request = UpstreamGuardianAdapter().build_from_evidence_vector(_m2_vector())

    assert request.user_id == "42"
    assert request.source_schema_version == "2.0.0"
    assert request.missing_baselines == ["hrv_rmssd"]
    assert request.critical_flags == []
    assert request.evidence[0].current_value is None
    assert request.evidence[0].baseline_value is None
    assert request.evidence[0].standardized_deviation == 2.2
    assert request.deviation_score == 2.2


def test_m2_signed_deviation_is_preserved_but_safety_magnitude_is_non_negative():
    vector = _m2_vector(evidence=[{
        "metric": "heart_rate", "direction": "below", "standardized_deviation": -1.75,
        "evidence_weight": 0.9, "quality_weight": 0.9,
    }])
    request = UpstreamGuardianAdapter().build_from_evidence_vector(vector)

    assert request.evidence[0].standardized_deviation == -1.75
    assert request.deviation_score == 1.75


def test_abstained_m2_vector_forces_remeasurement_and_no_alert():
    vector = _m2_vector(
        evidence=[],
        abstained=True,
        abstention_reasons=["insufficient usable metrics"],
    )
    request = UpstreamGuardianAdapter().build_from_evidence_vector(vector)
    engine = create_member3_engine("sqlite+pysqlite:///:memory:")
    Member3Base.metadata.create_all(engine)
    response = build_persistent_container(engine).guardian.process(request)

    assert request.upstream_abstained is True
    assert response.safety_action.value == "re_measure"
    assert response.alert.created is False
    assert response.notifications is None
    assert response.emergency_workflow is None


def test_m2_event_identifier_is_deterministic():
    adapter = UpstreamGuardianAdapter()
    vector = _m2_vector()
    assert adapter.build_from_evidence_vector(vector).event_id == adapter.build_from_evidence_vector(vector).event_id


def test_m2_contract_rejects_unknown_fields_and_false_non_diagnostic():
    with pytest.raises(ValidationError):
        _m2_vector(unexpected="value")
    with pytest.raises(ValidationError):
        _m2_vector(non_diagnostic=False)


def test_upstream_contract_rejects_unnormalized_or_non_finite_sleep_duration_deviation():
    from app.schemas.member3.upstream import M2EvidenceItem

    # M3 strictly rejects non-finite standardized deviations for sleep_duration
    with pytest.raises(ValidationError):
        M2EvidenceItem(
            metric="sleep_duration",
            direction="below",
            standardized_deviation=float("nan"),
            evidence_weight=0.8,
            quality_weight=0.8,
        )

    with pytest.raises(ValidationError):
        M2EvidenceItem(
            metric="sleep_duration",
            direction="below",
            standardized_deviation=float("inf"),
            evidence_weight=0.8,
            quality_weight=0.8,
        )

    # Valid normalized sleep deviation maps cleanly without fabricating raw hours or minutes
    valid_item = M2EvidenceItem(
        metric="sleep_duration",
        direction="below",
        standardized_deviation=-2.1,
        evidence_weight=0.9,
        quality_weight=0.95,
    )
    vector = _m2_vector(evidence=[valid_item])
    request = UpstreamGuardianAdapter().build_from_evidence_vector(vector)
    assert request.evidence[0].metric == "sleep_duration"
    assert request.evidence[0].standardized_deviation == -2.1
    assert request.evidence[0].current_value is None
    assert request.evidence[0].baseline_value is None
    assert request.evidence[0].unit is None
