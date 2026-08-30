"""Async SQLAlchemy engine/session configuration."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings


def _build_engine(database_url: str) -> AsyncEngine:
    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite+aiosqlite:///:memory:"):
        kwargs.update({"connect_args": {"check_same_thread": False}, "poolclass": StaticPool})
    elif database_url.startswith("sqlite+aiosqlite:"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_async_engine(database_url, **kwargs)


engine: AsyncEngine = _build_engine(settings.database_url)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def configure_database(database_url: str) -> AsyncEngine:
    """Reconfigure before app startup; primarily used by isolated integration tests."""

    global engine, SessionFactory
    engine = _build_engine(database_url)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_engine() -> AsyncEngine:
    return engine
