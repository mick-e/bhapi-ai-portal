"""Add missing tables and columns not covered by previous migrations.

Revision ID: 017
Revises: 016
Create Date: 2026-03-12

Missing objects found by model-vs-migration audit:
  Tables: setup_codes, auto_block_rules
  Columns: capture_events (content_encrypted, content_type, content_hash, enhanced_monitoring),
           risk_events (classifier_source),
           llm_accounts (last_error, last_sync_error, retry_count, next_retry_at),
           block_rules (auto_rule_id)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from migration_helpers import table_exists, column_exists

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Missing tables ---

    # setup_codes table (src/capture/models.py)
    if not table_exists("setup_codes"):
        op.create_table(
            "setup_codes",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("group_members.id"), nullable=False),
            sa.Column("code", sa.String(10), unique=True, nullable=False, index=True),
            sa.Column("signing_secret", sa.String(255), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used", sa.Boolean(), default=False, nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("device_name", sa.String(255), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # auto_block_rules table (src/blocking/models.py) — must be created BEFORE
    # block_rules.auto_rule_id FK references it
    if not table_exists("auto_block_rules"):
        op.create_table(
            "auto_block_rules",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False, server_default=""),
            sa.Column("trigger_type", sa.String(50), nullable=False),
            sa.Column("trigger_config", sa.JSON(), nullable=True),
            sa.Column("threshold", sa.Integer(), nullable=True),
            sa.Column("time_window_minutes", sa.Integer(), nullable=True),
            sa.Column("schedule_start", sa.String(5), nullable=True),
            sa.Column("schedule_end", sa.String(5), nullable=True),
            sa.Column("action", sa.String(50), nullable=False, server_default="block_all"),
            sa.Column("platforms", sa.JSON(), nullable=True),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("group_members.id"), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # --- Missing columns on capture_events ---
    if not column_exists("capture_events", "content_encrypted"):
        op.add_column("capture_events", sa.Column("content_encrypted", sa.Text(), nullable=True))

    if not column_exists("capture_events", "content_type"):
        op.add_column("capture_events", sa.Column("content_type", sa.String(50), nullable=True))

    if not column_exists("capture_events", "content_hash"):
        op.add_column("capture_events", sa.Column("content_hash", sa.String(64), nullable=True))

    if not column_exists("capture_events", "enhanced_monitoring"):
        op.add_column("capture_events", sa.Column("enhanced_monitoring", sa.Boolean(), server_default="0", nullable=False))

    # --- Missing column on risk_events ---
    if not column_exists("risk_events", "classifier_source"):
        op.add_column("risk_events", sa.Column("classifier_source", sa.String(50), server_default="keyword", nullable=True))

    # --- Missing columns on llm_accounts ---
    if not column_exists("llm_accounts", "last_error"):
        op.add_column("llm_accounts", sa.Column("last_error", sa.String(500), nullable=True))

    if not column_exists("llm_accounts", "last_sync_error"):
        op.add_column("llm_accounts", sa.Column("last_sync_error", sa.Text(), nullable=True))

    if not column_exists("llm_accounts", "retry_count"):
        op.add_column("llm_accounts", sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False))

    if not column_exists("llm_accounts", "next_retry_at"):
        op.add_column("llm_accounts", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))

    # --- Missing FK column on block_rules ---
    if not column_exists("block_rules", "auto_rule_id"):
        op.add_column(
            "block_rules",
            sa.Column("auto_rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        )


def downgrade() -> None:
    # Drop columns
    op.drop_column("block_rules", "auto_rule_id")
    op.drop_column("llm_accounts", "next_retry_at")
    op.drop_column("llm_accounts", "retry_count")
    op.drop_column("llm_accounts", "last_sync_error")
    op.drop_column("llm_accounts", "last_error")
    op.drop_column("risk_events", "classifier_source")
    op.drop_column("capture_events", "enhanced_monitoring")
    op.drop_column("capture_events", "content_hash")
    op.drop_column("capture_events", "content_type")
    op.drop_column("capture_events", "content_encrypted")
    # Drop tables
    op.drop_table("auto_block_rules")
    op.drop_table("setup_codes")
