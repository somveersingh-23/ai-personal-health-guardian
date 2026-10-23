def test_missing_digital_twin_artifact_returns_404(client):
    response = client.get("/api/member1/health-intelligence/999999/digital-twin")
    assert response.status_code == 404
