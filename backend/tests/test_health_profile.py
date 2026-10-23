def test_health_profile_create_and_read(client):
    payload = {
        "user_id": 9912,
        "age": 23,
        "height_cm": 165.0,
        "weight_kg": 55.0,
        "known_conditions": [],
        "medications": [],
        "allergies": ["none reported"],
    }
    created = client.post("/api/v1/member1/health-profile", json=payload)
    assert created.status_code == 200, created.text
    assert created.json()["user_id"] == payload["user_id"]

    fetched = client.get(f"/api/v1/member1/health-profile/{payload['user_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["weight_kg"] == 55.0


def test_missing_profile_returns_404(client):
    response = client.get("/api/v1/member1/health-profile/999999")
    assert response.status_code == 404
