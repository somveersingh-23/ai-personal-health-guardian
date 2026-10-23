from datetime import datetime, timezone


def test_health_event_create_list_update_delete(client):
    user_id = 9901
    payload = {
        "user_id": user_id,
        "event_type": "heart_rate",
        "event_time": datetime.now(timezone.utc).isoformat(),
        "value": 72.0,
        "unit": "bpm",
        "source": "pytest",
        "notes": "synthetic test event",
        "metadata_json": {"test": True},
    }
    created = client.post("/api/v1/member1/health-events", json=payload)
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]
    assert created.json()["user_id"] == user_id

    listed = client.get("/api/v1/member1/health-events", params={"user_id": user_id})
    assert listed.status_code == 200
    assert any(item["id"] == event_id for item in listed.json())

    updated = client.patch(
        f"/api/v1/member1/health-events/{event_id}",
        json={"value": 75.0, "notes": "updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["value"] == 75.0

    deleted = client.delete(f"/api/v1/member1/health-events/{event_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/v1/member1/health-events/{event_id}")
    assert missing.status_code == 404


def test_event_rejects_invalid_time_range(client):
    response = client.get(
        "/api/v1/member1/health-events",
        params={
            "user_id": 1,
            "start_time": "2026-10-22T00:00:00Z",
            "end_time": "2026-10-20T00:00:00Z",
        },
    )
    assert response.status_code == 400
