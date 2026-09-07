"""Real PostgreSQL races and migration ownership; requires a disposable audit DB."""

import asyncio
import os
import subprocess
import sys
from uuid import uuid4
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.member2 import HealthEvent
from app.schemas.member2 import HealthEventBatchCreate, InstantReadingCreate
from app.services.sensors.persistence_service import persist_batch, purge_member2_data
from app.services.sensors.transactions import CollectionPausedError


def database_url():
    url = os.environ.get("M2_POSTGRES_TEST_URL")
    if not url:
        pytest.skip("isolated PostgreSQL audit URL required")
    assert make_url(url).database.startswith("m2_audit_")
    return url


def test_concurrent_duplicate_uploads_and_purge_fence():
    url = database_url()

    async def scenario():
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(UTC) - timedelta(minutes=1)
        payload = InstantReadingCreate(
            metric="resting_heart_rate",
            unit="bpm",
            value=60,
            source="health_connect",
            observed_at=now,
            source_last_modified_at=now,
            data_origin_package="test.concurrent",
            source_record_type="RestingHeartRateRecord",
            source_record_id=str(uuid4()),
            recording_method="automatically_recorded",
            permission_state="granted_foreground",
        )
        batch = HealthEventBatchCreate(events=[payload])

        async def upload():
            async with sessions() as session:
                return await persist_batch(session, batch, 930003)

        results = await asyncio.gather(*(upload() for _ in range(16)))
        assert sum(item.inserted_count for item in results) == 1
        assert sum(item.duplicate_count for item in results) == 15
        async with sessions() as session:
            await purge_member2_data(session, 930003)
        blocked = await asyncio.gather(
            *(upload() for _ in range(8)), return_exceptions=True
        )
        assert all(isinstance(item, CollectionPausedError) for item in blocked)
        async with sessions() as session:
            assert not list(
                (
                    await session.scalars(
                        select(HealthEvent).where(HealthEvent.user_id == 930003)
                    )
                ).all()
            )
        await engine.dispose()

    asyncio.run(scenario())


def test_migration_downgrade_never_drops_m1_profile_table():
    url = database_url()
    env = dict(os.environ, DATABASE_URL=url)
    backend = Path(__file__).resolve().parents[2]

    async def profile_signature():
        engine = create_async_engine(url)
        async with engine.connect() as connection:
            columns = await connection.run_sync(
                lambda conn: inspect(conn).get_columns("health_profiles")
            )
            data = (
                await connection.execute(
                    text("SELECT * FROM health_profiles ORDER BY id")
                )
            ).all()
            signature = ([str(item) for item in columns], [str(item) for item in data])
        await engine.dispose()
        return signature

    before = asyncio.run(profile_signature())
    try:
        subprocess.run(
            [sys.executable, "-m", "alembic", "downgrade", "base"],
            cwd=backend,
            env=env,
            check=True,
            capture_output=True,
        )
        assert asyncio.run(profile_signature()) == before
    finally:
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=backend,
            env=env,
            check=True,
            capture_output=True,
        )
    assert asyncio.run(profile_signature()) == before


def test_member2_runtime_uses_migrations_and_excludes_research_routes(monkeypatch):
    url = database_url()
    from app.api.member2 import application
    from fastapi.testclient import TestClient

    monkeypatch.setattr(application.settings, "database_url", url)
    app = application.create_app()
    with TestClient(app) as client:
        assert client.get("/health/ready").status_code == 200
        assert client.get("/health/live").status_code == 200
        paths = client.get("/openapi.json").json()["paths"]
        assert "/api/v1/member2/events/batch" in paths
        assert not any(
            "preview" in path or "simulate" in path or "auth" in path for path in paths
        )
