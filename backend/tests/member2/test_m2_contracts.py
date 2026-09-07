"""M2 contract tests that are valid for the current M1 local integration.

They intentionally model the project's auth-free, single-user profile binding
and validate M2's strict data boundary.
"""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.member2 import (
    HealthEventBatchCreate,
    InstantReadingCreate,
    MetricType,
    PermissionState,
    RecordingMethod,
    SourceType,
)
from app.services.sensors import normalize_reading


NOW = datetime(2026, 1, 15, 12, tzinfo=UTC)


def health_connect_reading(**overrides: object) -> InstantReadingCreate:
    payload: dict[str, object] = {
        "metric": "resting_heart_rate",
        "unit": "bpm",
        "source": "health_connect",
        "observed_at": NOW.isoformat(),
        "value": 62,
        "data_origin_package": "com.example.watch",
        "source_record_type": "RestingHeartRateRecord",
        "source_record_id": "record-1",
        "source_last_modified_at": NOW.isoformat(),
        "device_id": "watch-1",
        "recording_method": "automatically_recorded",
        "permission_state": "granted_foreground",
    }
    payload.update(overrides)
    return InstantReadingCreate.model_validate(payload)


def test_health_connect_requires_source_identity() -> None:
    with pytest.raises(ValidationError, match="complete source identity"):
        health_connect_reading(source_record_id=None)


def test_health_connect_normalization_preserves_provenance_and_quality() -> None:
    event = normalize_reading(
        health_connect_reading(), user_id=7, received_at=NOW + timedelta(seconds=20)
    )
    assert event.user_id == 7
    assert event.metric is MetricType.RESTING_HEART_RATE
    assert event.source is SourceType.HEALTH_CONNECT
    assert event.data_origin_package == "com.example.watch"
    assert event.record_integrity_score > 0
    assert event.quality_vector.record_integrity_score > 0
    assert event.quality_vector.provenance_confidence > 0


def test_simulated_data_cannot_impersonate_a_live_sensor() -> None:
    with pytest.raises(ValidationError, match="simulated records require"):
        InstantReadingCreate.model_validate(
            {
                "metric": "resting_heart_rate",
                "unit": "bpm",
                "source": "simulated",
                "observed_at": NOW.isoformat(),
                "value": 62,
                "recording_method": RecordingMethod.AUTOMATICALLY_RECORDED.value,
                "permission_state": PermissionState.GRANTED_FOREGROUND.value,
            }
        )


def test_batch_rejects_mixed_schema_versions() -> None:
    reading = health_connect_reading().model_dump(mode="json")
    reading["schema_version"] = "3.0.0"
    reading["consent_receipt_id"] = "019bed3e-8100-7000-8000-000000000001"
    reading["purpose_version"] = "sensor-wellness-v1"
    with pytest.raises(
        ValidationError, match="batch and event schema versions must match"
    ):
        HealthEventBatchCreate.model_validate(
            {"schema_version": "2.0.0", "events": [reading]}
        )


def test_local_read_contract_is_bound_to_an_existing_m1_profile(
    tmp_path, app_factory
) -> None:
    """The temporary local bridge must not read/write arbitrary user IDs."""
    app = app_factory(f"sqlite+aiosqlite:///{(tmp_path / 'm2.db').as_posix()}")
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        assert client.get("/api/v1/member2/events?user_id=7").status_code == 404
        profile = client.post("/api/v1/member1/health-profile", json={"user_id": 7})
        assert profile.status_code == 200
        response = client.get("/api/v1/member2/events?user_id=7")
        assert response.status_code == 200
        assert response.json() == []

        observed_at = datetime.now(UTC) - timedelta(minutes=2)
        event = health_connect_reading(
            observed_at=observed_at.isoformat(),
            source_last_modified_at=observed_at.isoformat(),
        ).model_dump(mode="json")
        ingestion = client.post(
            "/api/v1/member2/events/batch?user_id=7",
            json={"schema_version": "2.0.0", "events": [event]},
        )
        assert ingestion.status_code == 200, ingestion.text

        exported = client.get("/api/v1/member2/data/export?user_id=7&limit=1")
        assert exported.status_code == 200, exported.text
        assert exported.json()["events"][0]["source_record_id"] == "record-1"
        assert exported.json()["has_more"] is False

        invalid = client.post(
            "/api/v1/member2/data/purge?user_id=7",
            json={"confirmation": "delete"},
        )
        assert invalid.status_code == 422

        purge = client.post(
            "/api/v1/member2/data/purge?user_id=7",
            json={"confirmation": "DELETE_MEMBER2_DATA"},
        )
        assert purge.status_code == 200, purge.text
        assert purge.json()["deleted_counts"]["health_events"] == 1
        assert client.get("/api/v1/member2/events?user_id=7").json() == []
        assert client.get("/api/v1/member1/health-profile/7").status_code == 200
        blocked = client.post(
            "/api/v1/member2/events/batch?user_id=7", json={"events": [event]}
        )
        assert blocked.status_code == 409
        assert (
            client.post(
                "/api/v1/member2/data/resume?user_id=7",
                json={"confirmation": "RESUME_MEMBER2_COLLECTION"},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/v1/member2/events/batch?user_id=7", json={"events": [event]}
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v1/member2/sync/reconcile/sessions/{'00000000-0000-0000-0000-000000000001'}/complete?user_id=7",
                json={"complete_snapshot": True},
            ).status_code
            == 422
        )
