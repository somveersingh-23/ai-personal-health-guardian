"""Contract and behavior tests for the production evidence fusion endpoint.

Tests POST /api/v1/member2/evidence/fuse:
1. Valid evidence request returns schema 2.0.0.
2. Valid feature vector is accepted.
3. Missing baseline is handled as unknown.
4. Abstained feature vector remains abstained.
5. Invalid user/profile access is rejected.
6. Invalid or inconsistent baseline deviation input is rejected safely.
7. Existing features/align endpoint remains unchanged and functional.
8. Production router actually exposes the new endpoint.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.schemas.member2 import (
    AggregationMethod,
    FusedMetric,
    MetricType,
    MultimodalFeatureVector,
    QualityDecision,
)


NOW = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)


def make_valid_feature_vector(user_id: int = 10, abstained: bool = False) -> dict:
    """Helper creating a schema 3.0.0 MultimodalFeatureVector payload."""
    features = [
        FusedMetric(
            metric=MetricType.RESTING_HEART_RATE,
            value=64.0,
            unit="bpm",
            aggregation_method=AggregationMethod.QUALITY_WEIGHTED_MEAN,
            sample_count=12,
            source_record_count=1,
            coverage_seconds=3600.0,
            quality_weight=0.92,
            quality_decision=QualityDecision.ACCEPTED,
            selected_source_keys=["health_connect:watch_1"],
            missing_quality_dimensions=[],
            source_event_ids=[str(uuid4())],
        ).model_dump(mode="json"),
        FusedMetric(
            metric=MetricType.HEART_RATE,
            value=78.0,
            unit="bpm",
            aggregation_method=AggregationMethod.QUALITY_WEIGHTED_MEAN,
            sample_count=60,
            source_record_count=1,
            coverage_seconds=3600.0,
            quality_weight=0.88,
            quality_decision=QualityDecision.ACCEPTED,
            selected_source_keys=["health_connect:watch_1"],
            missing_quality_dimensions=[],
            source_event_ids=[str(uuid4())],
        ).model_dump(mode="json"),
    ]
    return {
        "schema_version": "3.0.0",
        "user_id": user_id,
        "window_start": (NOW - timedelta(hours=1)).isoformat(),
        "window_end": NOW.isoformat(),
        "features": features,
        "missing_metrics": [],
        "composite_quality_score": 0.90,
        "composite_quality_status": "reliable",
        "abstained": abstained,
        "abstention_reasons": (
            ["insufficient_available_metrics", "composite_quality_below_threshold"]
            if abstained
            else []
        ),
        "contradictions": [],
        "provenance": {
            "sources": ["health_connect"],
            "devices": ["watch_1"],
            "algorithm": "quality-aware-late-fusion-v3",
            "non_diagnostic": True,
        },
    }


@pytest.fixture
def test_client(app_factory, tmp_path):
    app = app_factory(f"sqlite+aiosqlite:///{tmp_path / 'evidence.db'}")
    with TestClient(app) as client:
        # Create health profile for user 10
        resp = client.post("/api/v1/member1/health-profile", json={"user_id": 10})
        assert resp.status_code == 200
        yield client


def test_valid_evidence_request_returns_schema_2(test_client):
    """1. Valid evidence request returns schema 2.0.0."""
    vector_data = make_valid_feature_vector(user_id=10)
    payload = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": 1.2,
                "status": "above_normal",
            },
            {
                "metric": "heart_rate",
                "deviation_score": -0.8,
                "status": "below_normal",
            },
        ],
    }
    response = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["schema_version"] == "2.0.0"
    assert data["user_id"] == 10
    assert data["non_diagnostic"] is True
    assert data["abstained"] is False
    assert len(data["evidence"]) == 2
    assert data["combined_evidence_strength"] > 0.0
    assert data["missing_baselines"] == []

    # Check evidence items
    evidence_by_metric = {item["metric"]: item for item in data["evidence"]}
    assert "resting_heart_rate" in evidence_by_metric
    assert evidence_by_metric["resting_heart_rate"]["direction"] == "above"
    assert evidence_by_metric["resting_heart_rate"]["standardized_deviation"] == 1.2
    assert evidence_by_metric["resting_heart_rate"]["evidence_weight"] > 0.0
    assert evidence_by_metric["resting_heart_rate"]["quality_weight"] == 0.92

    assert "heart_rate" in evidence_by_metric
    assert evidence_by_metric["heart_rate"]["direction"] == "below"
    assert evidence_by_metric["heart_rate"]["standardized_deviation"] == -0.8


def test_valid_feature_vector_is_accepted(test_client):
    """2. Valid feature vector is accepted and fused."""
    vector_data = make_valid_feature_vector(user_id=10)
    # Validate through MultimodalFeatureVector schema first to ensure exact parity
    vector_obj = MultimodalFeatureVector.model_validate(vector_data)
    assert vector_obj.schema_version == "3.0.0"

    payload = {
        "vector": vector_obj.model_dump(mode="json"),
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": 0.0,
                "status": "normal",
            }
        ],
    }
    response = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["schema_version"] == "2.0.0"
    assert len(data["evidence"]) == 1
    assert data["evidence"][0]["direction"] == "normal"
    assert data["evidence"][0]["standardized_deviation"] == 0.0


def test_missing_baseline_is_handled_as_unknown(test_client):
    """3. Missing baseline is handled as unknown without fabricated values."""
    vector_data = make_valid_feature_vector(user_id=10)
    # Deviations only provide resting_heart_rate, heart_rate is missing
    payload = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": 1.5,
                "status": "above_normal",
            }
        ],
    }
    response = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "heart_rate" in data["missing_baselines"]
    assert len(data["evidence"]) == 1
    assert data["evidence"][0]["metric"] == "resting_heart_rate"

    # Explicit unknown status is also categorized as missing baseline
    payload_explicit_unknown = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": 0.0,
                "status": "unknown",
            },
            {
                "metric": "heart_rate",
                "deviation_score": 0.0,
                "status": "unknown",
            },
        ],
    }
    response_unknown = test_client.post(
        "/api/v1/member2/evidence/fuse?user_id=10", json=payload_explicit_unknown
    )
    assert response_unknown.status_code == 200
    data_unknown = response_unknown.json()
    assert set(data_unknown["missing_baselines"]) == {"resting_heart_rate", "heart_rate"}
    assert data_unknown["evidence"] == []
    assert data_unknown["abstained"] is True
    assert data_unknown["abstention_reasons"] == ["no_usable_baseline_evidence"]
    assert data_unknown["combined_evidence_strength"] == 0.0


def test_abstained_feature_vector_remains_abstained(test_client):
    """4. Abstained feature vector remains abstained."""
    vector_data = make_valid_feature_vector(user_id=10, abstained=True)
    payload = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": 1.2,
                "status": "above_normal",
            }
        ],
    }
    response = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["schema_version"] == "2.0.0"
    assert data["abstained"] is True
    assert data["evidence"] == []
    assert data["combined_evidence_strength"] == 0.0
    assert "input_feature_vector_abstained" in data["abstention_reasons"]
    assert "insufficient_available_metrics" in data["abstention_reasons"]
    assert "composite_quality_below_threshold" in data["abstention_reasons"]


def test_invalid_user_profile_access_is_rejected(test_client):
    """5. Invalid user/profile access is rejected."""
    vector_data = make_valid_feature_vector(user_id=10)
    payload = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": 0.5,
                "status": "normal",
            }
        ],
    }

    # User 9999 does not exist in health_profile -> 404
    resp_404 = test_client.post("/api/v1/member2/evidence/fuse?user_id=9999", json=payload)
    assert resp_404.status_code == 404
    assert "Create the Member 1 health profile" in resp_404.text

    # User_id query param missing -> 422
    resp_missing_user = test_client.post("/api/v1/member2/evidence/fuse", json=payload)
    assert resp_missing_user.status_code == 422

    # User_id query param <= 0 -> 422
    resp_zero_user = test_client.post("/api/v1/member2/evidence/fuse?user_id=0", json=payload)
    assert resp_zero_user.status_code == 422

    # Mismatched vector.user_id (10) vs query user_id (creates profile 11) -> 422
    test_client.post("/api/v1/member1/health-profile", json={"user_id": 11})
    resp_mismatch = test_client.post("/api/v1/member2/evidence/fuse?user_id=11", json=payload)
    assert resp_mismatch.status_code == 422
    assert "vector user_id must match" in resp_mismatch.text


def test_invalid_or_inconsistent_baseline_deviation_rejected(test_client):
    """6. Invalid or inconsistent baseline deviation input is rejected safely."""
    vector_data = make_valid_feature_vector(user_id=10)

    # Inconsistent: above_normal with negative deviation
    payload_above_neg = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": -1.5,
                "status": "above_normal",
            }
        ],
    }
    resp1 = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload_above_neg)
    assert resp1.status_code == 422
    assert "above_normal deviation_score cannot be negative" in resp1.text

    # Inconsistent: below_normal with positive deviation
    payload_below_pos = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": 1.5,
                "status": "below_normal",
            }
        ],
    }
    resp2 = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload_below_pos)
    assert resp2.status_code == 422
    assert "below_normal deviation_score cannot be positive" in resp2.text

    # Duplicate metrics in deviations
    payload_dup = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": 0.5,
                "status": "normal",
            },
            {
                "metric": "resting_heart_rate",
                "deviation_score": 0.7,
                "status": "normal",
            },
        ],
    }
    resp3 = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload_dup)
    assert resp3.status_code == 422
    assert "baseline_deviations must contain unique metrics" in resp3.text

    # Non-finite deviation score (e.g. NaN or string)
    payload_nan = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": "NaN",
                "status": "normal",
            }
        ],
    }
    resp4 = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload_nan)
    assert resp4.status_code == 422

    # Empty baseline_deviations
    payload_empty = {
        "vector": vector_data,
        "baseline_deviations": [],
    }
    resp5 = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload_empty)
    assert resp5.status_code == 422

    # Extra fabricated fields forbidden by STRICT_CONFIG
    payload_extra = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": 0.5,
                "status": "normal",
                "synthetic_clinical_risk": "critical",
            }
        ],
    }
    resp6 = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload_extra)
    assert resp6.status_code == 422


def test_features_align_endpoint_remains_unchanged(test_client):
    """7. Existing features/align endpoint remains unchanged and functional."""
    # First ingest a valid event for user 10
    now = datetime.now(UTC)
    consent_resp = test_client.post(
        "/api/v1/member2/consents?user_id=10",
        json={
            "purpose": "sensor_intelligence_wellness",
            "purpose_version": "v1",
            "notice_version": "v1",
            "granted_metrics": ["resting_heart_rate"],
            "granted_sources": ["health_connect"],
            "consented_at": now.isoformat(),
        },
    )
    assert consent_resp.status_code == 201, consent_resp.text
    receipt_id = consent_resp.json()["receipt_id"]

    event = {
        "schema_version": "3.0.0",
        "event_id": str(uuid4()),
        "metric": "resting_heart_rate",
        "temporal_type": "instant",
        "unit": "bpm",
        "value": 65.0,
        "source": "health_connect",
        "observed_at": (now - timedelta(minutes=10)).isoformat(),
        "data_origin_package": "com.test.watch",
        "source_record_type": "RestingHeartRateRecord",
        "source_record_id": "rhr-align-1",
        "source_last_modified_at": (now - timedelta(minutes=10)).isoformat(),
        "device_id": "watch_align",
        "recording_method": "automatically_recorded",
        "permission_state": "granted_foreground",
        "consent_receipt_id": receipt_id,
        "purpose_version": "v1",
    }
    batch_resp = test_client.post(
        "/api/v1/member2/events/batch?user_id=10",
        json={"schema_version": "3.0.0", "events": [event]},
    )
    assert batch_resp.status_code == 200, batch_resp.text

    # Align features
    align_resp = test_client.post(
        "/api/v1/member2/features/align?user_id=10",
        json={
            "window_start": (now - timedelta(hours=1)).isoformat(),
            "window_end": (now + timedelta(seconds=1)).isoformat(),
            "requested_metrics": ["resting_heart_rate"],
        },
    )
    assert align_resp.status_code == 200, align_resp.text
    data = align_resp.json()
    assert "vector" in data
    assert data["vector"]["schema_version"] == "3.0.0"
    assert data["vector"]["user_id"] == 10
    assert len(data["vector"]["features"]) == 1
    assert data["vector"]["features"][0]["metric"] == "resting_heart_rate"
    assert data["vector"]["features"][0]["value"] == 65.0


def test_production_router_exposes_evidence_fuse(monkeypatch):
    """8. Production router actually exposes the new endpoint without preview routes."""
    from app.api.member2 import application
    from app.api.member2.local import router

    # Verify endpoint is mounted on local router
    local_paths = {route.path for route in router.routes}
    assert "/api/v1/member2/evidence/fuse" in local_paths

    # Verify production app creation mounts it under /api/v1/member2/evidence/fuse
    monkeypatch.setattr(
        application.settings,
        "database_url",
        "postgresql+asyncpg://mock_user:mock_pass@localhost:5432/mock_db",
    )
    app = application.create_app()

    def _extract_routes(target):
        routes = []
        for r in getattr(target, "routes", []):
            if hasattr(r, "path"):
                routes.append(r)
            if hasattr(r, "original_router"):
                routes.extend(_extract_routes(r.original_router))
        return routes

    all_routes = _extract_routes(app)
    app_paths = {route.path for route in all_routes}
    assert "/api/v1/member2/evidence/fuse" in app_paths

    # Check method is POST
    post_routes = [
        route
        for route in all_routes
        if getattr(route, "path", None) == "/api/v1/member2/evidence/fuse"
    ]
    assert len(post_routes) == 1
    assert "POST" in post_routes[0].methods

    # Ensure no development preview/simulator routes are in production app
    assert not any("preview" in path or "simulate" in path for path in app_paths)


def test_invalid_status_and_infinity_rejected(test_client):
    """9. Invalid status strings and infinity are rejected with 422."""
    from pydantic import ValidationError
    from app.schemas.member2 import BaselineDeviation

    # Direct Pydantic validation rejects raw float inf and -inf
    for val in [float("inf"), float("-inf"), float("nan")]:
        with pytest.raises(ValidationError, match="deviation_score must be finite"):
            BaselineDeviation(
                metric=MetricType.RESTING_HEART_RATE,
                deviation_score=val,
                status="above_normal",
            )

    vector_data = make_valid_feature_vector(user_id=10)

    # Invalid status
    payload_bad_status = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": 1.5,
                "status": "critical_emergency",
            }
        ],
    }
    resp1 = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload_bad_status)
    assert resp1.status_code == 422

    # Positive infinity string in JSON
    payload_inf = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": "Infinity",
                "status": "above_normal",
            }
        ],
    }
    resp2 = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload_inf)
    assert resp2.status_code == 422

    # Negative infinity string in JSON
    payload_neginf = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": "-Infinity",
                "status": "below_normal",
            }
        ],
    }
    resp3 = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload_neginf)
    assert resp3.status_code == 422


def test_mixed_metrics_and_zero_quality_feature(test_client):
    """10. Mixed metrics with partial missing baselines and zero-quality weighting."""
    vector_data = make_valid_feature_vector(user_id=10)
    # Set one feature's quality_weight to 0.0 (corrupted sensor)
    vector_data["features"][1]["quality_weight"] = 0.0

    payload = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": 1.5,
                "status": "above_normal",
            },
            {
                "metric": "heart_rate",
                "deviation_score": 2.5,
                "status": "above_normal",
            },
        ],
    }
    resp = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["abstained"] is False
    assert len(data["evidence"]) == 2

    # Feature with 0.0 quality_weight has evidence_weight of 0.0 (cannot masquerade as strong evidence)
    evidence_by_metric = {item["metric"]: item for item in data["evidence"]}
    assert evidence_by_metric["heart_rate"]["quality_weight"] == 0.0
    assert evidence_by_metric["heart_rate"]["evidence_weight"] == 0.0
    assert evidence_by_metric["resting_heart_rate"]["evidence_weight"] > 0.0


def test_m3_adapter_schema_compatibility(test_client):
    """11. Output strictly matches M3 upstream consumer expectations for schema 2.0.0."""
    vector_data = make_valid_feature_vector(user_id=10)
    payload = {
        "vector": vector_data,
        "baseline_deviations": [
            {
                "metric": "resting_heart_rate",
                "deviation_score": -1.2,
                "status": "below_normal",
            },
            {
                "metric": "heart_rate",
                "deviation_score": 0.0,
                "status": "normal",
            },
        ],
    }
    resp = test_client.post("/api/v1/member2/evidence/fuse?user_id=10", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # M3 upstream expected fields
    assert data["schema_version"] == "2.0.0"
    assert isinstance(data["user_id"], int) and data["user_id"] > 0
    assert "window_start" in data and "window_end" in data
    assert "combined_evidence_strength" in data
    assert 0.0 <= data["combined_evidence_strength"] <= 1.0
    assert "missing_baselines" in data and isinstance(data["missing_baselines"], list)
    assert "abstained" in data and isinstance(data["abstained"], bool)
    assert "abstention_reasons" in data and isinstance(data["abstention_reasons"], list)
    assert data["non_diagnostic"] is True

    # Check evidence structure
    allowed_metrics = [
        "resting_heart_rate",
        "heart_rate",
        "spo2",
        "steps",
        "sleep_duration",
        "active_calories",
        "hrv_rmssd",
        "respiration_rate",
        "skin_temperature",
    ]
    for item in data["evidence"]:
        assert item["metric"] in allowed_metrics
        assert item["direction"] in ["below", "normal", "above", "unknown"]
        assert isinstance(item["standardized_deviation"], (int, float))
        assert 0.0 <= item["evidence_weight"] <= 1.0
        assert 0.0 <= item["quality_weight"] <= 1.0

