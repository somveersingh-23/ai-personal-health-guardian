"""Shared Member 2 test fixtures."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import create_access_token
from app.main import create_app

NOW = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(hours=3)


@pytest.fixture()
def app_settings(tmp_path):
    database_path = (tmp_path / "member2-test.db").as_posix()
    return Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{database_path}",
        jwt_secret="test-secret-with-at-least-thirty-two-characters",
        enable_preview_endpoints=True,
        auto_create_schema=True,
        max_request_bytes=32_000,
    )


@pytest.fixture()
def client(app_settings):
    with TestClient(create_app(app_settings)) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers(app_settings):
    token = create_access_token(7, app_settings, expires_minutes=5)
    return {"Authorization": f"Bearer {token}"}


def hc_common(record_type: str, record_id: str, modified: datetime | None = None) -> dict[str, object]:
    return {
        "schema_version": "2.0.0",
        "source": "health_connect",
        "data_origin_package": "com.example.watch",
        "source_record_type": record_type,
        "source_record_id": record_id,
        "source_last_modified_at": (modified or NOW).isoformat(),
        "device_id": "watch-1",
        "device_manufacturer": "Example",
        "device_model": "Watch One",
        "device_type": "watch",
        "recording_method": "automatically_recorded",
        "permission_state": "granted_background",
    }


def steps_payload(record_id: str, value: float, start: datetime = NOW, modified: datetime | None = None):
    return {
        **hc_common("StepsRecord", record_id, modified),
        "temporal_type": "interval",
        "metric": "steps",
        "unit": "count",
        "start_at": start.isoformat(),
        "end_at": start.replace(minute=59).isoformat(),
        "value": value,
    }


def heart_rate_payload(record_id: str, start: datetime = NOW):
    return {
        **hc_common("HeartRateRecord", record_id),
        "temporal_type": "series",
        "metric": "heart_rate",
        "unit": "bpm",
        "start_at": start.isoformat(),
        "end_at": start.replace(minute=59).isoformat(),
        "samples": [
            {"observed_at": start.replace(minute=10).isoformat(), "value": 70.0},
            {"observed_at": start.replace(minute=30).isoformat(), "value": 74.0},
        ],
    }
