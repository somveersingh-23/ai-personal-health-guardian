from datetime import datetime, timezone


def test_timeline_returns_newest_events_first(client):
    user_id = 9924
    for day, value in [("2026-10-20T08:00:00Z", 70), ("2026-10-22T08:00:00Z", 75)]:
        response = client.post("/api/v1/member1/health-events", json={
            "user_id": user_id,
            "event_type": "heart_rate",
            "event_time": day,
            "value": value,
            "unit": "bpm",
            "source": "pytest",
        })
        assert response.status_code == 201, response.text

    response = client.get(f"/api/v1/member1/health-timeline/{user_id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["count"] == 2
    assert data["events"][0]["value"] == 75
    assert data["events"][1]["value"] == 70
