"""COPPA 2026 compliance tables: third-party consent, retention policies,
push notification consent, video verification.

Revision ID: 031
Revises: 030
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Third-party consent items
    if not table_exists("third_party_consent_items"):
        op.create_table(
            "third_party_consent_items",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id"), nullable=False),
            sa.Column("parent_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("provider_key", sa.String(50), nullable=False),
            sa.Column("provider_name", sa.String(100), nullable=False),
            sa.Column("data_purpose", sa.String(500), nullable=False),
            sa.Column("consented", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_third_party_consent_group_member",
            "third_party_consent_items",
            ["group_id", "member_id"],
        )

    # Retention policies
    if not table_exists("retention_policies"):
        op.create_table(
            "retention_policies",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("data_type", sa.String(50), nullable=False),
            sa.Column("retention_days", sa.Integer(), nullable=False, server_default="365"),
            sa.Column("description", sa.String(500), nullable=False),
            sa.Column("auto_delete", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("last_cleanup_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("records_deleted", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_retention_policies_group_type",
            "retention_policies",
            ["group_id", "data_type"],
            unique=True,
        )

    # Push notification consents
    if not table_exists("push_notification_consents"):
        op.create_table(
            "push_notification_consents",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id"), nullable=False),
            sa.Column("parent_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("notification_type", sa.String(50), nullable=False),
            sa.Column("consented", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_push_consent_group_member",
            "push_notification_consents",
            ["group_id", "member_id"],
        )

    # Video verifications
    if not table_exists("video_verifications"):
        op.create_table(
            "video_verifications",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("parent_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("verification_method", sa.String(50), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("yoti_session_id", sa.String(255), nullable=True),
            sa.Column("verification_score", sa.Float(), nullable=True),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_video_verifications_group_parent",
            "video_verifications",
            ["group_id", "parent_user_id"],
        )


def downgrade() -> None:
    op.drop_table("video_verifications")
    op.drop_table("push_notification_consents")
    op.drop_table("retention_policies")
    op.drop_table("third_party_consent_items")
