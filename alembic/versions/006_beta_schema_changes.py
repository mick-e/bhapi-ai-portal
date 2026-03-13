"""Beta schema changes — new tables and columns for Beta release.

Revision ID: 006
Revises: 005
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from migration_helpers import table_exists, column_exists

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add renotify_count to alerts table
    if not column_exists("alerts", "renotify_count"):
        op.add_column(
            "alerts",
            sa.Column("renotify_count", sa.Integer(), nullable=False, server_default="0"),
        )

    # 2. fired_threshold_alerts table
    if not table_exists("fired_threshold_alerts"):
        op.create_table(
            "fired_threshold_alerts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("threshold_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("budget_thresholds.id"), nullable=False),
            sa.Column("percentage_level", sa.Integer(), nullable=False),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    # 3. human_review_requests table
    if not table_exists("human_review_requests"):
        op.create_table(
            "human_review_requests",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("risk_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("risk_events.id"), nullable=False),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("decision", sa.String(50), nullable=True),
            sa.Column("notes", sa.String(2000), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    # 4. appeal_records table
    if not table_exists("appeal_records"):
        op.create_table(
            "appeal_records",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("risk_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("risk_events.id"), nullable=False),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("reason", sa.String(2000), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("resolution", sa.String(50), nullable=True),
            sa.Column("resolution_notes", sa.String(2000), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    # 5. sis_connections table
    if not table_exists("sis_connections"):
        op.create_table(
            "sis_connections",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("credentials_encrypted", sa.String(1024), nullable=True),
            sa.Column("last_synced", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("config_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    # 6. block_rules table
    if not table_exists("block_rules"):
        op.create_table(
            "block_rules",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("group_members.id"), nullable=False),
            sa.Column("platforms", sa.JSON(), nullable=True),
            sa.Column("reason", sa.String(500), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    # 7. sso_configs table
    if not table_exists("sso_configs"):
        op.create_table(
            "sso_configs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("tenant_id", sa.String(255), nullable=True),
            sa.Column("auto_provision_members", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    # 8. sms_log table
    if not table_exists("sms_log"):
        op.create_table(
            "sms_log",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("to_phone", sa.String(20), nullable=False),
            sa.Column("message", sa.String(1600), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
            sa.Column("provider_sid", sa.String(100), nullable=True),
            sa.Column("error_message", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # 9. analytics_snapshots table
    if not table_exists("analytics_snapshots"):
        op.create_table(
            "analytics_snapshots",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("snapshot_type", sa.String(50), nullable=False),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
            sa.Column("data", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("analytics_snapshots")
    op.drop_table("sms_log")
    op.drop_table("sso_configs")
    op.drop_table("block_rules")
    op.drop_table("sis_connections")
    op.drop_table("appeal_records")
    op.drop_table("human_review_requests")
    op.drop_table("fired_threshold_alerts")
    op.drop_column("alerts", "renotify_count")
