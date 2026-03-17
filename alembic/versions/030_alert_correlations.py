"""Add alert_correlations table.

Revision ID: 027
Revises: 026
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("alert_correlations"):
        op.create_table(
            "alert_correlations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("correlation_type", sa.String(100), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("source_alerts", sa.JSON(), nullable=True),
            sa.Column("source_products", sa.JSON(), nullable=True),
            sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("acknowledged", sa.Boolean(), nullable=True, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("alert_correlations")
