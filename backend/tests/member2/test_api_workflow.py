"""M1-facing M2 API workflow, including idempotent staged synchronization."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient


def test_devices_consents_sync_pagination_and_fusion_contract(app_factory, tmp_path):
    now = datetime.now(UTC)
    with TestClient(
        app_factory(f"sqlite+aiosqlite:///{tmp_path / 'api.db'}")
    ) as client:
        assert (
            client.post(
                "/api/v1/member1/health-profile", json={"user_id": 7}
            ).status_code
            == 200
        )
        prefix = "/api/v1/member2"

        def post(path, payload):
            response = client.post(f"{prefix}{path}?user_id=7", json=payload)
            assert response.is_success, response.text
            return response.json()

        device = {
            "device": {
                "device_id": "watch",
                "source_type": "health_connect",
                "permission_state": "granted_foreground",
            }
        }
        assert client.put(f"{prefix}/devices?user_id=7", json=device).status_code == 200
        assert client.put(f"{prefix}/devices?user_id=7", json=device).status_code == 200
        capabilities = {
            "device_id": "watch",
            "capabilities": [
                {
                    "metric": "resting_heart_rate",
                    "source_record_type": "RestingHeartRateRecord",
                    "source_type": "health_connect",
                    "canonical_unit_ucum": "{beats}/min",
                }
            ],
        }
        assert (
            client.put(
                f"{prefix}/devices/capabilities?user_id=7", json=capabilities
            ).status_code
            == 200
        )
        capabilities["capabilities"][0]["support_status"] = "blocked"
        assert (
            client.put(
                f"{prefix}/devices/capabilities?user_id=7", json=capabilities
            ).status_code
            == 422
        )
        consent = post(
            "/consents",
            {
                "purpose": "sensor_intelligence_wellness",
                "purpose_version": "v1",
                "notice_version": "v1",
                "granted_metrics": ["resting_heart_rate"],
                "granted_sources": ["health_connect"],
                "consented_at": now.isoformat(),
            },
        )
        events = [
            dict(
                schema_version="3.0.0",
                event_id=str(uuid4()),
                metric="resting_heart_rate",
                temporal_type="instant",
                unit="bpm",
                value=60 + i,
                source="health_connect",
                observed_at=(now - timedelta(minutes=1)).isoformat(),
                data_origin_package="com.example.watch",
                source_record_type="RestingHeartRateRecord",
                source_record_id=f"r{i}",
                source_last_modified_at=(now - timedelta(minutes=1)).isoformat(),
                device_id="watch",
                device_type="watch",
                recording_method="automatically_recorded",
                permission_state="granted_foreground",
                consent_receipt_id=consent["receipt_id"],
                purpose_version="v1",
            )
            for i in range(2)
        ]
        assert (
            post("/events/batch", {"schema_version": "3.0.0", "events": events})[
                "inserted_count"
            ]
            == 2
        )
        page = client.get(f"{prefix}/data/export?user_id=7&limit=1").json()
        assert page["has_more"] and page["schema_version"] == "1.0.0"
        second = client.get(
            f"{prefix}/data/export?user_id=7&limit=1&after_id={page['next_after_id']}"
        ).json()
        assert not second["has_more"]
        assert page["events"][0]["id"] != second["events"][0]["id"]
        aligned = post(
            "/features/align",
            {
                "window_start": (now - timedelta(hours=1)).isoformat(),
                "window_end": (now + timedelta(seconds=1)).isoformat(),
                "requested_metrics": ["resting_heart_rate"],
            },
        )
        assert aligned["vector"]["features"][0]["value"] == 60.5
        snapshot = post(
            "/sync/reconcile/sessions",
            {
                "source_record_type": "RestingHeartRateRecord",
                "window_start": (now - timedelta(hours=1)).isoformat(),
                "window_end": now.isoformat(),
            },
        )
        path = f"/sync/reconcile/sessions/{snapshot['session_id']}"
        assert (
            post(path + "/records", {"source_record_ids": ["r0"]})["received_count"]
            == 1
        )
        assert (
            post(path + "/records", {"source_record_ids": ["r0"]})["duplicate_count"]
            == 1
        )
        assert (
            post(path + "/complete", {"complete_snapshot": True})[
                "tombstoned_stale_count"
            ]
            == 1
        )
        assert (
            post(path + "/complete", {"complete_snapshot": True})[
                "tombstoned_stale_count"
            ]
            == 1
        )
        cursor = {
            "record_type": "RestingHeartRateRecord",
            "token_fingerprint": "a" * 64,
            "last_successful_sync_at": now.isoformat(),
        }
        assert (
            client.put(f"{prefix}/sync/cursor?user_id=7", json=cursor).status_code
            == 200
        )
        assert (
            client.put(f"{prefix}/sync/cursor?user_id=7", json=cursor).status_code
            == 200
        )
        assert (
            post(
                f"/consents/{consent['receipt_id']}/withdraw",
                {"delete_linked_observations": True},
            )["deleted_observation_count"]
            == 1
        )
        assert client.get(f"{prefix}/events?user_id=7").json() == []
