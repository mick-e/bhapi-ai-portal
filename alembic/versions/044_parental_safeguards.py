"""Add parental safeguards tables: trusted_adult_requests, custody_configs, teen_privacy_configs.

Revision ID: 044
Revises: 043
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from migration_helpers import table_exists

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("trusted_adult_requests"):
        op.create_table(
            "trusted_adult_requests",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("child_member_id", UUID(as_uuid=True), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("trusted_adult_name", sa.String(255), nullable=True),
            sa.Column("trusted_adult_contact", sa.String(255), nullable=True),
            sa.Column("reason", sa.Text, nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("helplines_shown", sa.JSON, nullable=True),
            sa.Column("contacted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("processed_by", UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if not table_exists("custody_configs"):
        op.create_table(
            "custody_configs",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("child_member_id", UUID(as_uuid=True), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("guardian_member_id", UUID(as_uuid=True), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("role", sa.String(20), nullable=False, server_default="primary"),
            sa.Column("can_view_activity", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("can_manage_settings", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("can_approve_contacts", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("dispute_status", sa.String(20), nullable=False, server_default="none"),
            sa.Column("dispute_notes", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if not table_exists("teen_privacy_configs"):
        op.create_table(
            "teen_privacy_configs",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("child_member_id", UUID(as_uuid=True), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
            sa.Column("privacy_tier", sa.String(20), nullable=False),
            sa.Column("posts_visible", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("contacts_visible", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("messages_visible", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("activity_summary_only", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("flagged_content_visible", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("teen_privacy_configs")
    op.drop_table("custody_configs")
    op.drop_table("trusted_adult_requests")
