"""Real app, authentication, database, idempotency, deletion, and security tests."""

from datetime import timedelta

from app.main import create_app
from tests.member2.conftest import NOW, heart_rate_payload, steps_payload


def test_real_app_boots_and_exposes_member2_routes(client):
    assert client.get("/healthz").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/member2/events/batch" in paths
    assert "/api/v1/member2/sync/deletions" in paths
    assert "/api/v1/member2/sync/reconcile" in paths


def test_production_routes_require_authentication(client):
    response = client.post("/api/v1/member2/events/batch", json={"events": [steps_payload("one", 10)]})
    assert response.status_code == 401


def test_atomic_ingestion_idempotency_update_and_fingerprint_audit(client, auth_headers):
    payload = {"events": [steps_payload("steps-1", 100), heart_rate_payload("hr-1")]}
    first = client.post("/api/v1/member2/events/batch", json=payload, headers=auth_headers)
    assert first.status_code == 200, first.text
    assert first.json()["inserted_count"] == 2
    assert first.json()["duplicate_count"] == 0

    duplicate = client.post("/api/v1/member2/events/batch", json=payload, headers=auth_headers)
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["inserted_count"] == 0
    assert duplicate.json()["duplicate_count"] == 2

    changed = steps_payload("steps-1", 150, modified=NOW + timedelta(minutes=5))
    updated = client.post("/api/v1/member2/events/batch", json={"events": [changed]}, headers=auth_headers)
    assert updated.status_code == 200, updated.text
    assert updated.json()["updated_count"] == 1
    assert updated.json()["events"][0]["value"] == 150


def test_persisted_feature_alignment_uses_sum(client, auth_headers):
    payload = {
        "events": [
            steps_payload("steps-a", 100, NOW),
            steps_payload("steps-b", 200, NOW + timedelta(hours=1)),
        ]
    }
    assert client.post("/api/v1/member2/events/batch", json=payload, headers=auth_headers).status_code == 200
    response = client.post(
        "/api/v1/member2/features/align",
        json={
            "window_start": NOW.isoformat(),
            "window_end": (NOW + timedelta(hours=2)).isoformat(),
            "requested_metrics": ["steps"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["vector"]["features"][0]["value"] == 300


def test_source_deletion_propagates(client, auth_headers):
    assert client.post(
        "/api/v1/member2/events/batch",
        json={"events": [steps_payload("delete-me", 50)]},
        headers=auth_headers,
    ).status_code == 200
    response = client.post(
        "/api/v1/member2/sync/deletions",
        json={
            "source": "health_connect",
            "source_record_type": "StepsRecord",
            "source_record_ids": ["delete-me"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1


def test_expired_token_snapshot_reconciles_stale_records(client, auth_headers):
    payload = {
        "events": [
            steps_payload("snapshot-current", 100),
            steps_payload("snapshot-stale", 900),
        ]
    }
    assert client.post("/api/v1/member2/events/batch", json=payload, headers=auth_headers).status_code == 200
    response = client.post(
        "/api/v1/member2/sync/reconcile",
        json={
            "source": "health_connect",
            "source_record_type": "StepsRecord",
            "window_start": (NOW - timedelta(minutes=1)).isoformat(),
            "window_end": (NOW + timedelta(hours=2)).isoformat(),
            "source_record_ids": ["snapshot-current"],
            "complete_snapshot": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"authoritative_count": 1, "deleted_stale_count": 1}

    aligned = client.post(
        "/api/v1/member2/features/align",
        json={
            "window_start": NOW.isoformat(),
            "window_end": (NOW + timedelta(hours=1)).isoformat(),
            "requested_metrics": ["steps"],
        },
        headers=auth_headers,
    )
    assert aligned.status_code == 200, aligned.text
    assert aligned.json()["vector"]["features"][0]["value"] == 100


def test_reconciliation_requires_explicit_complete_snapshot(client, auth_headers):
    response = client.post(
        "/api/v1/member2/sync/reconcile",
        json={
            "source_record_type": "StepsRecord",
            "window_start": NOW.isoformat(),
            "window_end": (NOW + timedelta(hours=1)).isoformat(),
            "source_record_ids": [],
            "complete_snapshot": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_device_defaults_to_least_privilege(client, auth_headers):
    response = client.put(
        "/api/v1/member2/devices",
        json={"device": {"device_id": "watch-2", "source_type": "health_connect"}},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["permission_state"] == "unavailable"


def test_per_record_type_sync_cursor_is_persisted(client, auth_headers):
    response = client.put(
        "/api/v1/member2/sync/cursor",
        json={
            "record_type": "StepsRecord",
            "token_fingerprint": "a" * 64,
            "last_successful_sync_at": NOW.isoformat(),
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["record_type"] == "StepsRecord"
    assert "changes_token" not in response.json()
    assert response.json()["token_fingerprint"] == "a" * 64
    raw_token = client.put(
        "/api/v1/member2/sync/cursor",
        json={
            "record_type": "StepsRecord",
            "changes_token": "opaque-token",
            "last_successful_sync_at": NOW.isoformat(),
        },
        headers=auth_headers,
    )
    assert raw_token.status_code == 422


def test_payload_size_guard_rejects_oversized_requests(client, auth_headers):
    response = client.post(
        "/api/v1/member2/events/batch",
        content=b"x" * 40_000,
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert response.status_code == 413


def test_preview_can_be_disabled(app_settings):
    disabled = type(app_settings)(
        environment="test",
        database_url=app_settings.database_url,
        jwt_secret=app_settings.jwt_secret,
        enable_preview_endpoints=False,
        auto_create_schema=True,
    )
    app = create_app(disabled)
    assert not any(route.path.startswith("/api/v1/member2/preview") for route in app.routes)


def test_expired_or_invalid_token_is_rejected(client):
    response = client.put(
        "/api/v1/member2/devices",
        json={"device": {"device_id": "watch-3"}},
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert response.status_code == 401
