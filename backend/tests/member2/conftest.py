"""Isolated database/ASGI fixtures; never reuse app.main's cached engine."""

from contextlib import asynccontextmanager
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.fixture
def app_factory(monkeypatch):
    def create(database_url):
        monkeypatch.setenv("DATABASE_URL", database_url)
        from fastapi import FastAPI
        from app.database.database import get_db
        from app.database.base import Base
        from app.api.member1.health_profile import router as profiles
        from app.api.member2.local import router as sensors

        engine = create_async_engine(database_url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)

        @asynccontextmanager
        async def lifespan(app):
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            yield
            await engine.dispose()

        async def database():
            async with sessions() as session:
                yield session

        app = FastAPI(lifespan=lifespan)
        app.dependency_overrides[get_db] = database
        app.include_router(profiles)
        app.include_router(sensors)
        return app

    return create
