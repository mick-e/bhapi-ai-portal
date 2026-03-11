"""Add time budget tables for AI screen time limits.

Revision ID: 012
Revises: 011
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. time_budgets table
    op.create_table(
        "time_budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("group_members.id"), nullable=False),
        sa.Column("weekday_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("weekend_minutes", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("reset_hour", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("warn_at_percent", sa.Integer(), nullable=False, server_default="75"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_time_budgets_group_member", "time_budgets", ["group_id", "member_id"], unique=True)

    # 2. time_budget_usage table
    op.create_table(
        "time_budget_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("group_members.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("minutes_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("budget_minutes", sa.Integer(), nullable=False),
        sa.Column("exceeded", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("exceeded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_time_budget_usage_group_member_date", "time_budget_usage", ["group_id", "member_id", "date"], unique=True)


def downgrade() -> None:
    op.drop_table("time_budget_usage")
    op.drop_table("time_budgets")
