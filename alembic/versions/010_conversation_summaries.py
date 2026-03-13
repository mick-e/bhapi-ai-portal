"""Add conversation_summaries table for AI conversation summarization.

Revision ID: 010
Revises: 009
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from migration_helpers import table_exists, index_exists

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("conversation_summaries"):
        op.create_table(
            "conversation_summaries",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("group_members.id"), nullable=False),
            sa.Column("capture_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("capture_events.id"), nullable=True),
            sa.Column("platform", sa.String(50), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("topics", sa.JSON(), nullable=True),
            sa.Column("emotional_tone", sa.String(50), nullable=False, server_default="neutral"),
            sa.Column("risk_flags", sa.JSON(), nullable=True),
            sa.Column("key_quotes", sa.JSON(), nullable=True),
            sa.Column("action_needed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("action_reason", sa.String(500), nullable=True),
            sa.Column("summary_text", sa.Text(), nullable=False),
            sa.Column("detail_level", sa.String(20), nullable=False, server_default="full"),
            sa.Column("llm_model", sa.String(100), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    # Indexes for common query patterns
    if not index_exists("conversation_summaries", "ix_conv_summaries_content_hash"):
        op.create_index(
            "ix_conv_summaries_content_hash",
            "conversation_summaries",
            ["content_hash"],
        )
    if not index_exists("conversation_summaries", "ix_conv_summaries_group_member_date"):
        op.create_index(
            "ix_conv_summaries_group_member_date",
            "conversation_summaries",
            ["group_id", "member_id", "date"],
        )
    if not index_exists("conversation_summaries", "ix_conv_summaries_group_action"):
        op.create_index(
            "ix_conv_summaries_group_action",
            "conversation_summaries",
            ["group_id", "action_needed", "date"],
        )


def downgrade() -> None:
    op.drop_table("conversation_summaries")
