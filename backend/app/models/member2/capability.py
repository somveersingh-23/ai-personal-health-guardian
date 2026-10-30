"""Per-device, per-metric capability and validation evidence."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DeviceCapability(Base):
    __tablename__ = "device_capabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    source_record_type: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    support_status: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_unit_ucum: Mapped[str] = mapped_column(String(32), nullable=False)
    body_site: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sampling_rate_min_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    sampling_rate_max_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    measurement_resolution: Mapped[float | None] = mapped_column(Float, nullable=True)
    recording_methods_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    reference_method: Mapped[str | None] = mapped_column(String(256), nullable=True)
    calibration_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unverified")
    calibration_valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_protocol_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    known_limitations_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "uq_device_capability_identity",
            "user_id",
            "device_id",
            "metric",
            "source_record_type",
            unique=True,
        ),
    )


__all__ = ["DeviceCapability"]
