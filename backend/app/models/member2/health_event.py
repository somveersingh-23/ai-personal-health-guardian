"""Source-faithful normalized health records with database-enforced invariants."""

from datetime import UTC, datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, Float, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class HealthEvent(Base):
    __tablename__ = "health_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False, default="2.0.0")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    temporal_type: Mapped[str] = mapped_column(String(16), nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    source_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_unit_ucum: Mapped[str] = mapped_column(String(32), nullable=False)
    standard_code_system: Mapped[str | None] = mapped_column(String(128), nullable=True)
    standard_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone_offset_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_timezone_offset_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_timezone_offset_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    samples_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    stages_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    data_origin_package: Mapped[str] = mapped_column(String(256), nullable=False)
    source_record_type: Mapped[str] = mapped_column(String(128), nullable=False)
    source_record_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    client_record_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    client_record_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_last_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    device_manufacturer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    device_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    body_site: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sampling_rate_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    wear_state: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    motion_state: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    motion_artifact_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    recording_method: Mapped[str] = mapped_column(String(32), nullable=False)
    permission_state: Mapped[str] = mapped_column(String(32), nullable=False, default="unavailable")
    consent_receipt_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    processing_purpose: Mapped[str] = mapped_column(
        String(64), nullable=False, default="sensor_intelligence_wellness"
    )
    purpose_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retention_class: Mapped[str] = mapped_column(
        String(64), nullable=False, default="normalized_observation"
    )
    mapper_version: Mapped[str] = mapped_column(String(64), nullable=False, default="connector-mapper-v2")
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    record_integrity_score: Mapped[float] = mapped_column(Float, nullable=False)
    record_integrity_status: Mapped[str] = mapped_column(String(32), nullable=False)
    signal_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    freshness_status: Mapped[str] = mapped_column(String(32), nullable=False)
    data_freshness_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_flag: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_vector_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deletion_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "record_integrity_score >= 0 AND record_integrity_score <= 1",
            name="ck_event_integrity_score",
        ),
        CheckConstraint(
            "signal_quality_score IS NULL OR (signal_quality_score >= 0 AND signal_quality_score <= 1)",
            name="ck_event_signal_quality_score",
        ),
        CheckConstraint("data_freshness_seconds >= 0", name="ck_event_freshness_nonnegative"),
        CheckConstraint(
            "motion_artifact_score IS NULL OR "
            "(motion_artifact_score >= 0 AND motion_artifact_score <= 1)",
            name="ck_event_motion_artifact_score",
        ),
        CheckConstraint(
            "(lifecycle_status = 'deleted' AND deleted_at IS NOT NULL AND deletion_reason IS NOT NULL) "
            "OR (lifecycle_status != 'deleted' AND deleted_at IS NULL AND deletion_reason IS NULL)",
            name="ck_event_lifecycle_state",
        ),
        CheckConstraint(
            "(temporal_type = 'instant' AND observed_at IS NOT NULL AND value IS NOT NULL) OR "
            "(temporal_type = 'interval' AND start_at IS NOT NULL "
            "AND end_at IS NOT NULL AND value IS NOT NULL) OR "
            "(temporal_type = 'series' AND start_at IS NOT NULL AND end_at IS NOT NULL) OR "
            "(temporal_type = 'session' AND start_at IS NOT NULL AND end_at IS NOT NULL)",
            name="ck_event_temporal_shape",
        ),
        CheckConstraint(
            "end_at IS NULL OR start_at IS NULL OR end_at > start_at",
            name="ck_event_interval_order",
        ),
        Index("ix_health_events_user_metric_time", "user_id", "metric", "observed_at", "start_at", "end_at"),
        Index(
            "uq_health_events_source_identity",
            "user_id",
            "data_origin_package",
            "source_record_type",
            "source_record_id",
            unique=True,
            postgresql_where=text("source_record_id IS NOT NULL"),
            sqlite_where=text("source_record_id IS NOT NULL"),
        ),
    )
