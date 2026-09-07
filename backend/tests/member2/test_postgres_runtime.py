"""PostgreSQL integration smoke test for the shared M1/M2 data path."""

from datetime import UTC, datetime, timedelta
import os

import pytest


def test_postgres_profile_ingestion_and_read_contract(app_factory) -> None:
    database_url = os.getenv("M2_POSTGRES_TEST_URL")
    if not database_url:
        pytest.skip(
            "M2_POSTGRES_TEST_URL is required for the PostgreSQL integration test"
        )

    from sqlalchemy.engine import make_url

    assert make_url(database_url).database.startswith("m2_audit_"), (
        "Use an isolated audit database"
    )
    app = app_factory(database_url)
    from fastapi.testclient import TestClient

    observed_at = datetime.now(UTC) - timedelta(minutes=5)
    payload = {
        "schema_version": "2.0.0",
        "events": [
            {
                "schema_version": "2.0.0",
                "metric": "resting_heart_rate",
                "temporal_type": "instant",
                "unit": "bpm",
                "source": "health_connect",
                "observed_at": observed_at.isoformat(),
                "value": 62,
                "data_origin_package": "com.healthguardian.postgres.smoke",
                "source_record_type": "RestingHeartRateRecord",
                "source_record_id": "postgres-smoke-rhr-1",
                "source_last_modified_at": observed_at.isoformat(),
                "device_id": "postgres-smoke-watch",
                "recording_method": "automatically_recorded",
                "permission_state": "granted_foreground",
            }
        ],
    }

    with TestClient(app) as client:
        profile = client.post(
            "/api/v1/member1/health-profile", json={"user_id": 920_002}
        )
        assert profile.status_code == 200, profile.text

        ingestion = client.post(
            "/api/v1/member2/events/batch?user_id=920002", json=payload
        )
        assert ingestion.status_code == 200, ingestion.text
        assert ingestion.json()["inserted_count"] == 1

        records = client.get(
            "/api/v1/member2/events?user_id=920002&metrics=resting_heart_rate"
        )
        assert records.status_code == 200, records.text
        body = records.json()
        assert len(body) == 1
        assert body[0]["source_record_id"] == "postgres-smoke-rhr-1"
        assert body[0]["data_origin_package"] == "com.healthguardian.postgres.smoke"
        assert body[0]["quality_vector"]["provenance_confidence"] > 0

        exported = client.get("/api/v1/member2/data/export?user_id=920002&limit=1")
        assert exported.status_code == 200, exported.text
        assert (
            exported.json()["events"][0]["source_record_id"] == "postgres-smoke-rhr-1"
        )

        purge = client.post(
            "/api/v1/member2/data/purge?user_id=920002",
            json={"confirmation": "DELETE_MEMBER2_DATA"},
        )
        assert purge.status_code == 200, purge.text
        assert purge.json()["deleted_counts"]["health_events"] == 1
        assert client.get("/api/v1/member2/events?user_id=920002").json() == []
        assert client.get("/api/v1/member1/health-profile/920002").status_code == 200
