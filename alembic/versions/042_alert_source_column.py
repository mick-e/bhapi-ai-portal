"""Add source column to alerts for unified feed.

Revision ID: 042
Revises: 041
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "alerts",
        sa.Column("source", sa.String(20), nullable=False, server_default="ai"),
    )
    op.create_index(
        "ix_alerts_group_source_created", "alerts", ["group_id", "source", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_alerts_group_source_created", table_name="alerts")
    op.drop_column("alerts", "source")
