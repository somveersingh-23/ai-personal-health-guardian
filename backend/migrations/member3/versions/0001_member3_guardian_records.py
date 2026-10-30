"""Create durable Member 3 guardian record store.

Revision ID: member3_0001
"""

from alembic import op
import sqlalchemy as sa

revision = "member3_0001"
down_revision = None
branch_labels = ("member3",)
depends_on = None


def upgrade() -> None:
    op.create_table(
        "member3_guardian_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("record_type", sa.String(length=32), nullable=False),
        sa.Column("record_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("secondary_key", sa.String(length=256), nullable=True),
        sa.Column("metadata_value", sa.String(length=512), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_type", "record_id", name="uq_member3_record"),
    )
    op.create_index("ix_member3_user_type", "member3_guardian_records", ["user_id", "record_type"])
    op.create_index("ix_member3_secondary", "member3_guardian_records", ["record_type", "user_id", "secondary_key"])


def downgrade() -> None:
    op.drop_index("ix_member3_secondary", table_name="member3_guardian_records")
    op.drop_index("ix_member3_user_type", table_name="member3_guardian_records")
    op.drop_table("member3_guardian_records")
