"""Cross-app onboarding: child_invite_codes + parent_approval_requests tables.

Revision ID: 053
Revises: 052
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("child_invite_codes"):
        op.create_table(
            "child_invite_codes",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("code", sa.String(6), nullable=False, unique=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
        )
        op.create_index("ix_child_invite_codes_code", "child_invite_codes", ["code"])

    if not table_exists("parent_approval_requests"):
        op.create_table(
            "parent_approval_requests",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("parent_email", sa.String(255), nullable=False),
            sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
        )
        op.create_index("ix_parent_approval_requests_token_hash", "parent_approval_requests", ["token_hash"])
        op.create_index("ix_parent_approval_requests_child_id", "parent_approval_requests", ["child_id"])


def downgrade() -> None:
    op.drop_table("parent_approval_requests")
    op.drop_table("child_invite_codes")
