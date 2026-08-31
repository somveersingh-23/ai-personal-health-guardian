"""Create shared health profile and Member 2 sensor-intelligence tables.

Revision ID: 0001_member2
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_member2"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "health_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("known_conditions", sa.JSON(), nullable=True),
        sa.Column("medications", sa.JSON(), nullable=True),
        sa.Column("allergies", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_health_profiles_id", "health_profiles", ["id"])
    op.create_index("ix_health_profiles_user_id", "health_profiles", ["user_id"])

    op.create_table(
        "health_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("temporal_type", sa.String(length=16), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone_offset_minutes", sa.Integer(), nullable=True),
        sa.Column("start_timezone_offset_minutes", sa.Integer(), nullable=True),
        sa.Column("end_timezone_offset_minutes", sa.Integer(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("samples_json", sa.JSON(), nullable=False),
        sa.Column("stages_json", sa.JSON(), nullable=False),
        sa.Column("data_origin_package", sa.String(length=256), nullable=False),
        sa.Column("source_record_type", sa.String(length=128), nullable=False),
        sa.Column("source_record_id", sa.String(length=256), nullable=True),
        sa.Column("source_last_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_id", sa.String(length=128), nullable=True),
        sa.Column("device_manufacturer", sa.String(length=128), nullable=True),
        sa.Column("device_model", sa.String(length=128), nullable=True),
        sa.Column("device_type", sa.String(length=64), nullable=True),
        sa.Column("recording_method", sa.String(length=32), nullable=False),
        sa.Column("permission_state", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("record_integrity_score", sa.Float(), nullable=False),
        sa.Column("record_integrity_status", sa.String(length=32), nullable=False),
        sa.Column("signal_quality_score", sa.Float(), nullable=True),
        sa.Column("signal_quality_status", sa.String(length=32), nullable=False),
        sa.Column("freshness_status", sa.String(length=32), nullable=False),
        sa.Column("data_freshness_seconds", sa.Integer(), nullable=False),
        sa.Column("validation_flag", sa.String(length=32), nullable=False),
        sa.Column("validation_reason", sa.Text(), nullable=True),
        sa.Column("quality_policy_version", sa.String(length=64), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "record_integrity_score >= 0 AND record_integrity_score <= 1",
            name="ck_event_integrity_score",
        ),
        sa.CheckConstraint(
            "signal_quality_score IS NULL OR (signal_quality_score >= 0 AND signal_quality_score <= 1)",
            name="ck_event_signal_quality_score",
        ),
        sa.CheckConstraint("data_freshness_seconds >= 0", name="ck_event_freshness_nonnegative"),
        sa.CheckConstraint(
            "(temporal_type = 'instant' AND observed_at IS NOT NULL AND value IS NOT NULL) OR "
            "(temporal_type = 'interval' AND start_at IS NOT NULL "
            "AND end_at IS NOT NULL AND value IS NOT NULL) OR "
            "(temporal_type = 'series' AND start_at IS NOT NULL AND end_at IS NOT NULL) OR "
            "(temporal_type = 'session' AND start_at IS NOT NULL AND end_at IS NOT NULL)",
            name="ck_event_temporal_shape",
        ),
        sa.CheckConstraint(
            "end_at IS NULL OR start_at IS NULL OR end_at > start_at",
            name="ck_event_interval_order",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_health_events_event_id"),
    )
    op.create_index("ix_health_events_metric", "health_events", ["metric"])
    op.create_index("ix_health_events_source", "health_events", ["source"])
    op.create_index("ix_health_events_user_id", "health_events", ["user_id"])
    op.create_index(
        "ix_health_events_user_metric_time",
        "health_events",
        ["user_id", "metric", "observed_at", "start_at", "end_at"],
    )
    op.create_index(
        "uq_health_events_source_identity",
        "health_events",
        ["user_id", "data_origin_package", "source_record_type", "source_record_id"],
        unique=True,
        postgresql_where=sa.text("source_record_id IS NOT NULL"),
        sqlite_where=sa.text("source_record_id IS NOT NULL"),
    )

    op.create_table(
        "sensor_ingestion_audits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload_size_bytes", sa.Integer(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sensor_ingestion_audits_payload_sha256",
        "sensor_ingestion_audits",
        ["payload_sha256"],
    )
    op.create_index("ix_sensor_ingestion_audits_user_id", "sensor_ingestion_audits", ["user_id"])

    op.create_table(
        "device_registries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("manufacturer", sa.String(length=128), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("firmware_version", sa.String(length=64), nullable=True),
        sa.Column("device_type", sa.String(length=64), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("permission_state", sa.String(length=32), nullable=False),
        sa.Column("battery_level", sa.Float(), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("last_sync_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_device_registries_user_id", "device_registries", ["user_id"])
    op.create_index(
        "uq_device_registries_user_device",
        "device_registries",
        ["user_id", "device_id"],
        unique=True,
    )

    op.create_table(
        "health_connect_sync_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("record_type", sa.String(length=128), nullable=False),
        sa.Column("changes_token", sa.String(length=4096), nullable=False),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_health_connect_sync_states_user_id", "health_connect_sync_states", ["user_id"])
    op.create_index(
        "uq_sync_state_user_record_type",
        "health_connect_sync_states",
        ["user_id", "record_type"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_sync_state_user_record_type", table_name="health_connect_sync_states")
    op.drop_index("ix_health_connect_sync_states_user_id", table_name="health_connect_sync_states")
    op.drop_table("health_connect_sync_states")
    op.drop_index("uq_device_registries_user_device", table_name="device_registries")
    op.drop_index("ix_device_registries_user_id", table_name="device_registries")
    op.drop_table("device_registries")
    op.drop_index("ix_sensor_ingestion_audits_user_id", table_name="sensor_ingestion_audits")
    op.drop_index("ix_sensor_ingestion_audits_payload_sha256", table_name="sensor_ingestion_audits")
    op.drop_table("sensor_ingestion_audits")
    op.drop_index("uq_health_events_source_identity", table_name="health_events")
    op.drop_index("ix_health_events_user_metric_time", table_name="health_events")
    op.drop_index("ix_health_events_user_id", table_name="health_events")
    op.drop_index("ix_health_events_source", table_name="health_events")
    op.drop_index("ix_health_events_metric", table_name="health_events")
    op.drop_table("health_events")
    op.drop_index("ix_health_profiles_user_id", table_name="health_profiles")
    op.drop_index("ix_health_profiles_id", table_name="health_profiles")
    op.drop_table("health_profiles")
