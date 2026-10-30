"""Alembic environment for async PostgreSQL and SQLite smoke tests."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.database.base import Base
import os
try:
    from app.database.database import settings
    _db_url = getattr(settings, "database_url", None)
except Exception:
    _db_url = None

if not _db_url:
    _db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./health_guardian.db")
import app.models.member2  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", _db_url.replace("%", "%%"))
target_metadata = Base.metadata

MEMBER2_TABLES = {
    "member2_sensor_events",
    "device_registries",
    "health_connect_sync_states",
    "sensor_ingestion_audits",
    "consent_receipts",
    "device_capabilities",
    "source_tombstones",
    "reconciliation_sessions",
    "reconciliation_records",
    "sensor_collection_states",
}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in MEMBER2_TABLES
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    import asyncio

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
