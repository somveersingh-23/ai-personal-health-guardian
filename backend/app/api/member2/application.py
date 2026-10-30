"""M2-only PostgreSQL runtime with migrations managed outside application startup."""

from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.member2.local import router
from app.database.database import get_db

MIGRATION_HEAD = "0003_member2"
logger = logging.getLogger("member2.application")


class _Settings:
    @property
    def database_url(self) -> str:
        return os.getenv("DATABASE_URL", "")

    @database_url.setter
    def database_url(self, value: str) -> None:
        os.environ["DATABASE_URL"] = value


settings = _Settings()


def create_app() -> FastAPI:
    if not settings.database_url.startswith("postgresql+asyncpg://"):
        raise ValueError("M2 runtime requires PostgreSQL with the asyncpg driver")
    engine = create_async_engine(
        settings.database_url, echo=False, hide_parameters=True, pool_pre_ping=True
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def verify_schema():
        async with engine.connect() as connection:
            revision = await connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )
            if revision != MIGRATION_HEAD:
                raise RuntimeError(
                    "M2 database migration is not at the required revision"
                )
            # M1 owns profile initialization; startup only checks this contract.
            await connection.execute(
                text("SELECT user_id FROM health_profiles LIMIT 0")
            )

    @asynccontextmanager
    async def lifespan(app):
        try:
            await verify_schema()
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="Health Guardian Member 2", lifespan=lifespan)

    async def database():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = database
    app.include_router(router)

    @app.get("/health/live", include_in_schema=False)
    async def live():
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    async def ready():
        try:
            await verify_schema()
        except Exception as exc:
            logger.error("Database readiness check failed: %s", exc, exc_info=exc)
            raise HTTPException(status_code=503, detail="database not ready") from exc
        return {"status": "ready"}

    return app
