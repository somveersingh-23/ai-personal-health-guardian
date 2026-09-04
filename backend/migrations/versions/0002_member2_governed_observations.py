"""Add governed observation v3, capabilities, consent, tombstones and staged sync.

Revision ID: 0002_member2
Revises: 0001_member2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_member2"
down_revision: str | Sequence[str] | None = "0001_member2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _upgrade_health_events() -> None:
    with op.batch_alter_table("health_events") as batch:
        batch.add_column(sa.Column("source_unit", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("canonical_unit_ucum", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("standard_code_system", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("standard_code", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("client_record_id", sa.String(length=256), nullable=True))
        batch.add_column(sa.Column("client_record_version", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("body_site", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("sampling_rate_hz", sa.Float(), nullable=True))
        batch.add_column(
            sa.Column("wear_state", sa.String(length=32), nullable=False, server_default="unknown")
        )
        batch.add_column(
            sa.Column("motion_state", sa.String(length=32), nullable=False, server_default="unknown")
        )
        batch.add_column(sa.Column("motion_artifact_score", sa.Float(), nullable=True))
        batch.add_column(sa.Column("consent_receipt_id", sa.String(length=36), nullable=True))
        batch.add_column(
            sa.Column(
                "processing_purpose",
                sa.String(length=64),
                nullable=False,
                server_default="sensor_intelligence_wellness",
            )
        )
        batch.add_column(sa.Column("purpose_version", sa.String(length=64), nullable=True))
        batch.add_column(
            sa.Column(
                "retention_class",
                sa.String(length=64),
                nullable=False,
                server_default="normalized_observation",
            )
        )
        batch.add_column(
            sa.Column(
                "mapper_version",
                sa.String(length=64),
                nullable=False,
                server_default="connector-mapper-v2",
            )
        )
        batch.add_column(sa.Column("quality_vector_json", sa.JSON(), nullable=True))
        batch.add_column(
            sa.Column("lifecycle_status", sa.String(length=32), nullable=False, server_default="active")
        )
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("deletion_reason", sa.String(length=128), nullable=True))

    op.execute("UPDATE health_events SET source_unit = unit")
    op.execute(
        """
        UPDATE health_events SET canonical_unit_ucum = CASE metric
          WHEN 'heart_rate' THEN '{beats}/min'
          WHEN 'resting_heart_rate' THEN '{beats}/min'
          WHEN 'hrv_rmssd' THEN 'ms'
          WHEN 'spo2' THEN '%'
          WHEN 'respiration_rate' THEN '{breaths}/min'
          WHEN 'skin_temperature' THEN 'Cel'
          WHEN 'steps' THEN '{count}'
          WHEN 'sleep_duration' THEN 'min'
          WHEN 'active_calories' THEN 'kcal'
          ELSE unit END
        """
    )
    op.execute(
        """
        UPDATE health_events SET standard_code_system = 'http://loinc.org', standard_code =
          CASE metric
            WHEN 'heart_rate' THEN '8867-4'
            WHEN 'spo2' THEN '59408-5'
            WHEN 'respiration_rate' THEN '9279-1'
            WHEN 'steps' THEN '41950-7'
            WHEN 'sleep_duration' THEN '93832-4'
            ELSE NULL END
        WHERE metric IN ('heart_rate', 'spo2', 'respiration_rate', 'steps', 'sleep_duration')
        """
    )
    vector = (
        '{"policy_version":"quality-vector-v2","decision":"unknown",'
        '"record_integrity_score":0.5,"signal_quality_score":null,'
        '"provenance_confidence":0.5,"freshness_score":0.25,"coverage_score":null,'
        '"wear_confidence":null,"motion_artifact_score":null,'
        '"calibration_confidence":null,"device_validation_confidence":null,'
        '"reason_codes":["migrated_legacy_observation"]}'
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        statement = sa.text(
            "UPDATE health_events SET quality_vector_json = CAST(:value AS JSON)"
        ).bindparams(value=vector)
        op.execute(statement)
    else:
        op.execute(sa.text("UPDATE health_events SET quality_vector_json = :value").bindparams(value=vector))

    with op.batch_alter_table("health_events") as batch:
        batch.alter_column("source_unit", existing_type=sa.String(length=32), nullable=False)
        batch.alter_column("canonical_unit_ucum", existing_type=sa.String(length=32), nullable=False)
        batch.alter_column("quality_vector_json", existing_type=sa.JSON(), nullable=False)
        batch.create_index("ix_health_events_consent_receipt_id", ["consent_receipt_id"])
        batch.create_index("ix_health_events_lifecycle_status", ["lifecycle_status"])
        batch.create_check_constraint(
            "ck_event_motion_artifact_score",
            "motion_artifact_score IS NULL OR "
            "(motion_artifact_score >= 0 AND motion_artifact_score <= 1)",
        )
        batch.create_check_constraint(
            "ck_event_lifecycle_state",
            "(lifecycle_status = 'deleted' AND deleted_at IS NOT NULL "
            "AND deletion_reason IS NOT NULL) OR "
            "(lifecycle_status != 'deleted' AND deleted_at IS NULL AND deletion_reason IS NULL)",
        )


def upgrade() -> None:
    _upgrade_health_events()
    with op.batch_alter_table("health_connect_sync_states") as batch:
        batch.add_column(sa.Column("token_fingerprint", sa.String(length=64), nullable=True))
    # Invalidate legacy server-side tokens. Android owns the encrypted cursor;
    # the backend retains only a non-reversible fingerprint for audit correlation.
    op.execute(
        "UPDATE health_connect_sync_states SET changes_token = 'redacted', "
        "token_fingerprint = "
        "'0000000000000000000000000000000000000000000000000000000000000000'"
    )
    with op.batch_alter_table("health_connect_sync_states") as batch:
        batch.alter_column(
            "token_fingerprint", existing_type=sa.String(length=64), nullable=False
        )
    op.create_table(
        "consent_receipts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("receipt_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("purpose_version", sa.String(length=64), nullable=False),
        sa.Column("notice_version", sa.String(length=64), nullable=False),
        sa.Column("granted_metrics_json", sa.JSON(), nullable=False),
        sa.Column("granted_sources_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_id"),
    )
    op.create_index("ix_consent_receipts_user_id", "consent_receipts", ["user_id"])
    op.create_index("ix_consent_user_status", "consent_receipts", ["user_id", "status"])

    op.create_table(
        "device_capabilities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("source_record_type", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("support_status", sa.String(length=32), nullable=False),
        sa.Column("canonical_unit_ucum", sa.String(length=32), nullable=False),
        sa.Column("body_site", sa.String(length=64), nullable=True),
        sa.Column("sampling_rate_min_hz", sa.Float(), nullable=True),
        sa.Column("sampling_rate_max_hz", sa.Float(), nullable=True),
        sa.Column("measurement_resolution", sa.Float(), nullable=True),
        sa.Column("recording_methods_json", sa.JSON(), nullable=False),
        sa.Column("reference_method", sa.String(length=256), nullable=True),
        sa.Column("calibration_status", sa.String(length=32), nullable=False),
        sa.Column("calibration_valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_protocol_version", sa.String(length=64), nullable=True),
        sa.Column("known_limitations_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_device_capabilities_user_id", "device_capabilities", ["user_id"])
    op.create_index(
        "uq_device_capability_identity",
        "device_capabilities",
        ["user_id", "device_id", "metric", "source_record_type"],
        unique=True,
    )

    op.create_table(
        "source_tombstones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_record_type", sa.String(length=128), nullable=False),
        sa.Column("source_record_id", sa.String(length=256), nullable=False),
        sa.Column("consent_receipt_id", sa.String(length=36), nullable=True),
        sa.Column("reason", sa.String(length=128), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_tombstones_user_id", "source_tombstones", ["user_id"])
    op.create_index(
        "uq_source_tombstone_identity",
        "source_tombstones",
        ["user_id", "source", "source_record_type", "source_record_id"],
        unique=True,
    )

    op.create_table(
        "reconciliation_sessions",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_record_type", sa.String(length=128), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("received_record_count", sa.Integer(), nullable=False),
        sa.Column("tombstoned_stale_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index("ix_reconciliation_sessions_user_id", "reconciliation_sessions", ["user_id"])
    op.create_index(
        "ix_reconciliation_user_status",
        "reconciliation_sessions",
        ["user_id", "status"],
    )
    op.create_table(
        "reconciliation_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("source_record_id", sa.String(length=256), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"], ["reconciliation_sessions.session_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reconciliation_records_session_id", "reconciliation_records", ["session_id"])
    op.create_index(
        "uq_reconciliation_session_record",
        "reconciliation_records",
        ["session_id", "source_record_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_reconciliation_session_record", table_name="reconciliation_records")
    op.drop_index("ix_reconciliation_records_session_id", table_name="reconciliation_records")
    op.drop_table("reconciliation_records")
    op.drop_index("ix_reconciliation_user_status", table_name="reconciliation_sessions")
    op.drop_index("ix_reconciliation_sessions_user_id", table_name="reconciliation_sessions")
    op.drop_table("reconciliation_sessions")
    op.drop_index("uq_source_tombstone_identity", table_name="source_tombstones")
    op.drop_index("ix_source_tombstones_user_id", table_name="source_tombstones")
    op.drop_table("source_tombstones")
    op.drop_index("uq_device_capability_identity", table_name="device_capabilities")
    op.drop_index("ix_device_capabilities_user_id", table_name="device_capabilities")
    op.drop_table("device_capabilities")
    op.drop_index("ix_consent_user_status", table_name="consent_receipts")
    op.drop_index("ix_consent_receipts_user_id", table_name="consent_receipts")
    op.drop_table("consent_receipts")

    with op.batch_alter_table("health_connect_sync_states") as batch:
        batch.drop_column("token_fingerprint")

    with op.batch_alter_table("health_events") as batch:
        batch.drop_constraint("ck_event_lifecycle_state", type_="check")
        batch.drop_constraint("ck_event_motion_artifact_score", type_="check")
        batch.drop_index("ix_health_events_lifecycle_status")
        batch.drop_index("ix_health_events_consent_receipt_id")
        for column in (
            "deletion_reason",
            "deleted_at",
            "lifecycle_status",
            "quality_vector_json",
            "mapper_version",
            "retention_class",
            "purpose_version",
            "processing_purpose",
            "consent_receipt_id",
            "motion_artifact_score",
            "motion_state",
            "wear_state",
            "sampling_rate_hz",
            "body_site",
            "client_record_version",
            "client_record_id",
            "standard_code",
            "standard_code_system",
            "canonical_unit_ucum",
            "source_unit",
        ):
            batch.drop_column(column)
