"""Audit, device registry, and per-record-type sync state models."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SensorIngestionAudit(Base):
    """Stores request metadata fingerprints and counts, never raw health/waveform/image payloads."""

    __tablename__ = "sensor_ingestion_audits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


# Alias for backward compatibility
RawSensorAudit = SensorIngestionAudit


class DeviceRegistry(Base):
    __tablename__ = "device_registries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    permission_state: Mapped[str] = mapped_column(String(32), nullable=False, default="unavailable")
    battery_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    capabilities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_sync_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    __table_args__ = (Index("uq_device_registries_user_device", "user_id", "device_id", unique=True),)


class HealthConnectSyncState(Base):
    __tablename__ = "health_connect_sync_states"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    record_type: Mapped[str] = mapped_column(String(128), nullable=False)
    changes_token: Mapped[str] = mapped_column(String(4096), nullable=False)
    token_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    last_successful_sync_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    __table_args__ = (Index("uq_sync_state_user_record_type", "user_id", "record_type", unique=True),)
