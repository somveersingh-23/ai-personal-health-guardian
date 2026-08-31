"""Governed-v3, device-policy, tombstone and staged-reconciliation tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.schemas.member2 import InstantReadingCreate, MetricType, SeriesReadingCreate, SeriesSample
from app.services.sensors import assess_record_integrity, fuse_events, normalize_reading
from tests.member2.conftest import NOW, hc_common, steps_payload


def _consent_payload(receipt_id: str) -> dict[str, object]:
    return {
        "receipt_id": receipt_id,
        "purpose": "sensor_intelligence_wellness",
        "purpose_version": "wellness-v1",
        "notice_version": "privacy-v1",
        "granted_metrics": ["steps", "heart_rate"],
        "granted_sources": ["health_connect"],
        "consented_at": NOW.isoformat(),
        "expires_at": (NOW + timedelta(days=30)).isoformat(),
    }


def _v3_steps(receipt_id: str, record_id: str, value: float = 100.0) -> dict[str, object]:
    payload = steps_payload(record_id, value)
    payload.update(
        {
            "schema_version": "3.0.0",
            "consent_receipt_id": receipt_id,
            "processing_purpose": "sensor_intelligence_wellness",
            "purpose_version": "wellness-v1",
            "retention_class": "normalized_observation",
            "mapper_version": "health-connect-android-v3",
            "wear_state": "worn",
            "motion_state": "moving",
        }
    )
    return payload


def test_v3_live_observation_requires_consent_context(client, auth_headers):
    payload = steps_payload("v3-no-consent", 100)
    payload["schema_version"] = "3.0.0"
    response = client.post(
        "/api/v1/member2/events/batch",
        json={"schema_version": "3.0.0", "events": [payload]},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "consent_receipt_id" in response.text


def test_active_consent_and_observed_device_enrich_quality_vector(client, auth_headers):
    receipt_id = str(uuid4())
    consent = client.post(
        "/api/v1/member2/consents",
        json=_consent_payload(receipt_id),
        headers=auth_headers,
    )
    assert consent.status_code == 201, consent.text

    device = client.put(
        "/api/v1/member2/devices",
        json={"device": {"device_id": "watch-1", "source_type": "health_connect"}},
        headers=auth_headers,
    )
    assert device.status_code == 200, device.text
    capabilities = client.put(
        "/api/v1/member2/devices/capabilities",
        json={
            "device_id": "watch-1",
            "capabilities": [
                {
                    "metric": "steps",
                    "source_record_type": "StepsRecord",
                    "source_type": "health_connect",
                    "support_status": "experimental",
                    "canonical_unit_ucum": "{count}",
                    "recording_methods": ["automatically_recorded"],
                    "calibration_status": "unverified",
                }
            ],
        },
        headers=auth_headers,
    )
    assert capabilities.status_code == 200, capabilities.text

    response = client.post(
        "/api/v1/member2/events/batch",
        json={
            "schema_version": "3.0.0",
            "events": [_v3_steps(receipt_id, "governed-step")],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    event = response.json()["events"][0]
    assert event["canonical_unit_ucum"] == "{count}"
    assert event["standard_code"] == "41950-7"
    assert event["quality_vector"]["device_validation_confidence"] == 0.6
    assert event["quality_vector"]["calibration_confidence"] is None


def test_client_cannot_self_certify_or_block_a_device(client, auth_headers):
    assert client.put(
        "/api/v1/member2/devices",
        json={"device": {"device_id": "watch-1", "source_type": "health_connect"}},
        headers=auth_headers,
    ).status_code == 200
    response = client.put(
        "/api/v1/member2/devices/capabilities",
        json={
            "device_id": "watch-1",
            "capabilities": [
                {
                    "metric": "steps",
                    "source_record_type": "StepsRecord",
                    "source_type": "health_connect",
                    "support_status": "blocked",
                    "canonical_unit_ucum": "{count}",
                    "calibration_status": "unverified",
                    "known_limitations": ["failed validation"],
                }
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "self-certify" in response.text


def test_consent_withdrawal_deletes_linked_data_and_tombstone_blocks_stale_replay(
    client,
    auth_headers,
):
    receipt_id = str(uuid4())
    assert client.post(
        "/api/v1/member2/consents",
        json=_consent_payload(receipt_id),
        headers=auth_headers,
    ).status_code == 201
    original = _v3_steps(receipt_id, "withdraw-step")
    assert client.post(
        "/api/v1/member2/events/batch",
        json={"schema_version": "3.0.0", "events": [original]},
        headers=auth_headers,
    ).status_code == 200
    withdrawn = client.post(
        f"/api/v1/member2/consents/{receipt_id}/withdraw",
        json={"delete_linked_observations": True, "reason": "user_withdrawal"},
        headers=auth_headers,
    )
    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.json()["deleted_observation_count"] == 1

    replay = client.post(
        "/api/v1/member2/events/batch",
        json={"schema_version": "3.0.0", "events": [original]},
        headers=auth_headers,
    )
    assert replay.status_code == 422
    assert "consent is not active" in replay.text


def test_source_tombstone_blocks_stale_replay_but_allows_newer_correction(client, auth_headers):
    original = steps_payload("deleted-step", 100)
    assert client.post(
        "/api/v1/member2/events/batch", json={"events": [original]}, headers=auth_headers
    ).status_code == 200
    deletion_time = datetime.now(UTC)
    deleted = client.post(
        "/api/v1/member2/sync/deletions",
        json={
            "source": "health_connect",
            "source_record_type": "StepsRecord",
            "source_record_ids": ["deleted-step"],
            "deleted_at": deletion_time.isoformat(),
        },
        headers=auth_headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["tombstoned_count"] == 1

    stale = client.post(
        "/api/v1/member2/events/batch", json={"events": [original]}, headers=auth_headers
    )
    assert stale.status_code == 200
    assert stale.json()["duplicate_count"] == 1
    assert stale.json()["events"] == []

    newer = steps_payload(
        "deleted-step",
        150,
        modified=deletion_time + timedelta(minutes=1),
    )
    corrected = client.post(
        "/api/v1/member2/events/batch", json={"events": [newer]}, headers=auth_headers
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["inserted_count"] == 1


def test_staged_reconciliation_accepts_multiple_chunks_and_is_idempotent(client, auth_headers):
    assert client.post(
        "/api/v1/member2/events/batch",
        json={"events": [steps_payload("keep", 10), steps_payload("remove", 20)]},
        headers=auth_headers,
    ).status_code == 200
    session_id = str(uuid4())
    started = client.post(
        "/api/v1/member2/sync/reconcile/sessions",
        json={
            "session_id": session_id,
            "source": "health_connect",
            "source_record_type": "StepsRecord",
            "window_start": (NOW - timedelta(minutes=1)).isoformat(),
            "window_end": (NOW + timedelta(hours=2)).isoformat(),
        },
        headers=auth_headers,
    )
    assert started.status_code == 201, started.text
    first = client.post(
        f"/api/v1/member2/sync/reconcile/sessions/{session_id}/records",
        json={"source_record_ids": ["keep"] + [f"external-{index}" for index in range(499)]},
        headers=auth_headers,
    )
    assert first.status_code == 200, first.text
    second = client.post(
        f"/api/v1/member2/sync/reconcile/sessions/{session_id}/records",
        json={"source_record_ids": ["keep", "external-500"]},
        headers=auth_headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["duplicate_count"] == 1

    completed = client.post(
        f"/api/v1/member2/sync/reconcile/sessions/{session_id}/complete",
        json={"complete_snapshot": True},
        headers=auth_headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["authoritative_count"] == 501
    assert completed.json()["tombstoned_stale_count"] == 1
    repeated = client.post(
        f"/api/v1/member2/sync/reconcile/sessions/{session_id}/complete",
        json={"complete_snapshot": True},
        headers=auth_headers,
    )
    assert repeated.status_code == 200
    assert repeated.json()["tombstoned_stale_count"] == 1


def test_claim_registry_exposes_prohibited_features(client, auth_headers):
    response = client.get("/api/v1/member2/claims", headers=auth_headers)
    assert response.status_code == 200
    claims = {item["feature_id"]: item for item in response.json()}
    assert claims["phone-camera-spo2"]["claim_class"] == "prohibited"
    assert claims["ppg-derived-respiration"]["claim_class"] == "prohibited"


def test_consent_receipt_is_idempotent_but_immutable(client, auth_headers):
    receipt_id = str(uuid4())
    payload = _consent_payload(receipt_id)
    first = client.post("/api/v1/member2/consents", json=payload, headers=auth_headers)
    second = client.post("/api/v1/member2/consents", json=payload, headers=auth_headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    changed = {**payload, "notice_version": "privacy-v2"}
    collision = client.post("/api/v1/member2/consents", json=changed, headers=auth_headers)
    assert collision.status_code == 422
    assert "immutable" in collision.text


def test_device_capability_can_be_safely_reclassified(client, auth_headers):
    assert client.put(
        "/api/v1/member2/devices",
        json={"device": {"device_id": "watch-1", "source_type": "health_connect"}},
        headers=auth_headers,
    ).status_code == 200
    base = {
        "metric": "steps",
        "source_record_type": "StepsRecord",
        "source_type": "health_connect",
        "canonical_unit_ucum": "{count}",
        "calibration_status": "unverified",
    }
    assert client.put(
        "/api/v1/member2/devices/capabilities",
        json={"device_id": "watch-1", "capabilities": [{**base, "support_status": "experimental"}]},
        headers=auth_headers,
    ).status_code == 200
    updated = client.put(
        "/api/v1/member2/devices/capabilities",
        json={
            "device_id": "watch-1",
            "capabilities": [
                {
                    **base,
                    "support_status": "experimental",
                    "known_limitations": ["updated after device observation"],
                }
            ],
        },
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["capabilities"][0]["support_status"] == "experimental"
    assert updated.json()["capabilities"][0]["known_limitations"] == [
        "updated after device observation"
    ]


def test_completed_reconciliation_rejects_new_chunks(client, auth_headers):
    session_id = str(uuid4())
    payload = {
        "session_id": session_id,
        "source": "health_connect",
        "source_record_type": "StepsRecord",
        "window_start": NOW.isoformat(),
        "window_end": (NOW + timedelta(hours=1)).isoformat(),
    }
    first = client.post(
        "/api/v1/member2/sync/reconcile/sessions", json=payload, headers=auth_headers
    )
    repeated = client.post(
        "/api/v1/member2/sync/reconcile/sessions", json=payload, headers=auth_headers
    )
    assert first.status_code == repeated.status_code == 201
    assert client.post(
        f"/api/v1/member2/sync/reconcile/sessions/{session_id}/records",
        json={"source_record_ids": ["one"]},
        headers=auth_headers,
    ).status_code == 200
    assert client.post(
        f"/api/v1/member2/sync/reconcile/sessions/{session_id}/complete",
        json={"complete_snapshot": True},
        headers=auth_headers,
    ).status_code == 200
    rejected = client.post(
        f"/api/v1/member2/sync/reconcile/sessions/{session_id}/records",
        json={"source_record_ids": ["late"]},
        headers=auth_headers,
    )
    assert rejected.status_code == 422
    assert "not collecting" in rejected.text


def test_fusion_reports_cross_source_contradiction_and_explicit_abstention():
    readings = []
    for package, record_id, value in (
        ("com.watch.a", "hr-a", 60.0),
        ("com.watch.b", "hr-b", 100.0),
    ):
        common = hc_common("HeartRateRecord", record_id)
        common["data_origin_package"] = package
        readings.append(
            SeriesReadingCreate(
                **common,
                metric="heart_rate",
                unit="bpm",
                start_at=NOW,
                end_at=NOW + timedelta(minutes=1),
                samples=[SeriesSample(observed_at=NOW, value=value)],
            )
        )
    events = [normalize_reading(item, 7, NOW + timedelta(minutes=2)) for item in readings]
    vector = fuse_events(
        events,
        [MetricType.HEART_RATE, MetricType.SPO2],
        NOW,
        NOW + timedelta(minutes=1),
        min_available_metrics=2,
    )
    assert "heart_rate:source_disagreement" in vector.contradictions
    assert vector.missing_metrics == [MetricType.SPO2]
    assert vector.abstained is True
    assert "insufficient_available_metrics" in vector.abstention_reasons


def test_quality_vector_preserves_measured_coverage_wear_and_motion_dimensions():
    common = hc_common("HeartRateRecord", "quality-vector-series")
    reading = SeriesReadingCreate(
        **common,
        metric="heart_rate",
        unit="bpm",
        start_at=NOW,
        end_at=NOW + timedelta(seconds=10),
        samples=[
            SeriesSample(observed_at=NOW, value=70),
            SeriesSample(observed_at=NOW + timedelta(seconds=5), value=72),
        ],
        sampling_rate_hz=1.0,
        wear_state="worn",
        motion_state="moving",
        motion_artifact_score=0.2,
    )
    result = assess_record_integrity(reading, NOW + timedelta(seconds=20))
    assert result.quality_vector.coverage_score == 0.2
    assert result.quality_vector.wear_confidence == 1.0
    assert result.quality_vector.motion_artifact_score == 0.2
    assert "wear_state_unknown" not in result.quality_vector.reason_codes
    assert "motion_state_unknown" not in result.quality_vector.reason_codes


def test_quality_vector_distinguishes_source_trust_and_historical_freshness():
    research = InstantReadingCreate(
        schema_version="2.0.0",
        source="research_dataset",
        data_origin_package="research.bidmc",
        source_record_type="BIDMCReferenceSpO2",
        source_record_id="bidmc-quality-1",
        device_id="bidmc:quality",
        device_type="research_reference",
        recording_method="automatically_recorded",
        permission_state="unavailable",
        metric="spo2",
        unit="%",
        observed_at=NOW - timedelta(days=2),
        value=98,
    )
    research_result = assess_record_integrity(research, NOW)
    assert research_result.quality_vector.provenance_confidence == 0.85
    assert research_result.quality_vector.freshness_score == 0.50

    manual = InstantReadingCreate(
        source="manual_entry",
        recording_method="manual_entry",
        metric="spo2",
        unit="%",
        observed_at=NOW - timedelta(days=8),
        value=98,
    )
    manual_result = assess_record_integrity(manual, NOW)
    assert manual_result.quality_vector.provenance_confidence == 0.45
    assert manual_result.quality_vector.freshness_score == 0.25

    unknown_device = InstantReadingCreate(
        **{
            **hc_common("OxygenSaturationRecord", "unknown-device-quality"),
            "device_id": None,
            "device_manufacturer": None,
            "device_model": None,
            "device_type": None,
            "recording_method": "unknown",
        },
        metric="spo2",
        unit="%",
        observed_at=NOW,
        value=98,
    )
    unknown_result = assess_record_integrity(unknown_device, NOW)
    assert "recording method is unknown" in unknown_result.validation_reason
