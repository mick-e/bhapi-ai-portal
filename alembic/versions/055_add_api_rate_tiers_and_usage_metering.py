"""Add API platform rate tiers and usage metering tables.

Revision ID: 055
Revises: 054
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa
from migration_helpers import table_exists

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # API key → rate tier mapping
    if not table_exists("api_key_rate_tiers"):
        op.create_table(
            "api_key_rate_tiers",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("api_key_id", sa.Uuid(), nullable=False),
            sa.Column("tier_name", sa.String(30), nullable=False, server_default="free"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_api_key_rate_tiers_api_key_id",
            "api_key_rate_tiers",
            ["api_key_id"],
            unique=True,
        )

    # Per-request usage log
    if not table_exists("api_request_logs"):
        op.create_table(
            "api_request_logs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("api_key_id", sa.Uuid(), nullable=False),
            sa.Column("endpoint", sa.String(255), nullable=False),
            sa.Column("status_code", sa.Integer(), nullable=False),
            sa.Column("response_time_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_api_request_logs_key_created",
            "api_request_logs",
            ["api_key_id", "created_at"],
        )

    # Monthly usage aggregates
    if not table_exists("api_usage_monthly_aggregates"):
        op.create_table(
            "api_usage_monthly_aggregates",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("api_key_id", sa.Uuid(), nullable=False),
            sa.Column("year_month", sa.String(7), nullable=False),
            sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("avg_response_time_ms", sa.Float(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_api_usage_monthly_key_month",
            "api_usage_monthly_aggregates",
            ["api_key_id", "year_month"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_table("api_usage_monthly_aggregates")
    op.drop_table("api_request_logs")
    op.drop_table("api_key_rate_tiers")
