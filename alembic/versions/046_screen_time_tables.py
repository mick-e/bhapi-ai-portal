"""Create screen time tables — rules, schedules, extension requests.

Revision ID: 046
Revises: 045
Create Date: 2026-03-23
"""

import sqlalchemy as sa
from alembic import op
from migration_helpers import table_exists

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # screen_time_rules — per-app/category daily limits for a child
    if not table_exists("screen_time_rules"):
        op.create_table(
            "screen_time_rules",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("app_category", sa.String(30), nullable=False, server_default="all"),
            sa.Column("daily_limit_minutes", sa.Integer(), nullable=False),
            sa.Column("age_tier_enforcement", sa.String(30), nullable=False, server_default="warning_then_block"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_screen_time_rules_member_id", "screen_time_rules", ["member_id"])
        op.create_index("ix_screen_time_rules_group_member", "screen_time_rules", ["group_id", "member_id"])

    # screen_time_schedules — time-of-day blocked windows attached to a rule
    if not table_exists("screen_time_schedules"):
        op.create_table(
            "screen_time_schedules",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("rule_id", sa.Uuid(), sa.ForeignKey("screen_time_rules.id", ondelete="CASCADE"), nullable=False),
            sa.Column("day_type", sa.String(20), nullable=False, server_default="weekday"),
            sa.Column("blocked_start", sa.Time(), nullable=False),
            sa.Column("blocked_end", sa.Time(), nullable=False),
            sa.Column("description", sa.String(200), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_screen_time_schedules_rule_id", "screen_time_schedules", ["rule_id"])

    # extension_requests — child requests for additional screen time
    if not table_exists("extension_requests"):
        op.create_table(
            "extension_requests",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("rule_id", sa.Uuid(), sa.ForeignKey("screen_time_rules.id", ondelete="CASCADE"), nullable=False),
            sa.Column("requested_minutes", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("responded_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_extension_requests_member_id", "extension_requests", ["member_id"])
        op.create_index("ix_extension_requests_member_status", "extension_requests", ["member_id", "status"])


def downgrade() -> None:
    op.drop_table("extension_requests")
    op.drop_table("screen_time_schedules")
    op.drop_table("screen_time_rules")
