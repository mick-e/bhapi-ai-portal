"""Add AI usage policies and violations tables.

Revision ID: 025
Revises: 024
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("ai_usage_policies"):
        op.create_table(
            "ai_usage_policies",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("policy_type", sa.String(50), nullable=False),
            sa.Column("rules", sa.JSON(), nullable=True),
            sa.Column("enforcement_level", sa.String(20), nullable=False, server_default="warn"),
            sa.Column("applies_to", sa.JSON(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not table_exists("policy_violations"):
        op.create_table(
            "policy_violations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("violation_type", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("action_taken", sa.String(50), nullable=False, server_default="logged"),
            sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("policy_violations")
    op.drop_table("ai_usage_policies")
