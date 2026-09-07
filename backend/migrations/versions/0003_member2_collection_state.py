"""Persist collection pause after M2 purge without altering M1 tables."""

import sqlalchemy as sa
from alembic import op

revision = "0003_member2"
down_revision = "0002_member2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sensor_collection_states",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("paused", sa.Boolean(), nullable=False),
    )


def downgrade():
    op.drop_table("sensor_collection_states")
