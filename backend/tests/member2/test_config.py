"""Fail-closed configuration tests for sensitive Member 2 routes."""

import pytest

from app.core.config import Settings


def test_unknown_environment_cannot_bypass_production_checks():
    with pytest.raises(ValueError, match="APP_ENV"):
        Settings(environment="prodution")


def test_production_cannot_enable_preview_routes():
    with pytest.raises(ValueError, match="preview"):
        Settings(
            environment="production",
            database_url="postgresql+asyncpg://user:password@database/health",
            jwt_secret="a-unique-production-secret-with-32-chars",
            enable_preview_endpoints=True,
            auto_create_schema=False,
        )


def test_invalid_boolean_environment_value_is_rejected(monkeypatch):
    monkeypatch.setenv("ENABLE_PREVIEW_ENDPOINTS", "flase")
    with pytest.raises(ValueError, match="invalid boolean"):
        Settings.from_env()


@pytest.mark.parametrize("minutes", [0, 1_441])
def test_access_token_lifetime_is_bounded(minutes):
    with pytest.raises(ValueError, match="ACCESS_TOKEN_MINUTES"):
        Settings(access_token_minutes=minutes)


@pytest.mark.parametrize("size", [16_383, 10_485_761])
def test_request_size_limit_is_bounded(size):
    with pytest.raises(ValueError, match="MAX_REQUEST_BYTES"):
        Settings(max_request_bytes=size)
