"""Device agent tables — sessions, app usage, screen time.

Revision ID: 039
Revises: 038
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from migration_helpers import table_exists

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Device sessions table
    if not table_exists("device_sessions"):
        op.create_table(
            "device_sessions",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("device_id", sa.String(255), nullable=False),
            sa.Column("device_type", sa.String(50), nullable=False),
            sa.Column("os_version", sa.String(50), nullable=True),
            sa.Column("app_version", sa.String(50), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("battery_level", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_device_sessions_member_id", "device_sessions", ["member_id"])
        op.create_index("ix_device_sessions_group_id", "device_sessions", ["group_id"])
        op.create_index("ix_device_sessions_member_started", "device_sessions", ["member_id", "started_at"])

    # App usage records table
    if not table_exists("app_usage_records"):
        op.create_table(
            "app_usage_records",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("session_id", sa.Uuid(), sa.ForeignKey("device_sessions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("app_name", sa.String(255), nullable=False),
            sa.Column("bundle_id", sa.String(500), nullable=False),
            sa.Column("category", sa.String(50), nullable=False, server_default="other"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("foreground_minutes", sa.Float(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_app_usage_member_id", "app_usage_records", ["member_id"])
        op.create_index("ix_app_usage_group_id", "app_usage_records", ["group_id"])
        op.create_index("ix_app_usage_member_started", "app_usage_records", ["member_id", "started_at"])
        op.create_index("ix_app_usage_member_category", "app_usage_records", ["member_id", "category"])

    # Screen time records table
    if not table_exists("screen_time_records"):
        op.create_table(
            "screen_time_records",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("total_minutes", sa.Float(), nullable=False, server_default="0"),
            sa.Column("app_breakdown", sa.JSON(), nullable=True),
            sa.Column("category_breakdown", sa.JSON(), nullable=True),
            sa.Column("pickups", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_screen_time_member_id", "screen_time_records", ["member_id"])
        op.create_index("ix_screen_time_group_id", "screen_time_records", ["group_id"])
        op.create_index("ix_screen_time_member_date", "screen_time_records", ["member_id", "date"], unique=True)


def downgrade() -> None:
    op.drop_table("screen_time_records")
    op.drop_table("app_usage_records")
    op.drop_table("device_sessions")
