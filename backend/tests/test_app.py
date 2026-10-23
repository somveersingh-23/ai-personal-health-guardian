def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_contains_member1_routes(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/member1/health-events" in paths
    assert "/api/v1/member1/health-profile" in paths
    assert "/api/v1/member1/health-timeline/{user_id}" in paths
