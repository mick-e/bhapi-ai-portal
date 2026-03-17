"""Add URL filter rules and categories tables.

Revision ID: 026
Revises: 025
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("url_filter_rules"):
        op.create_table(
            "url_filter_rules",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column("action", sa.String(20), nullable=False, server_default="block"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not table_exists("url_categories"):
        op.create_table(
            "url_categories",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("key", sa.String(50), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("url_patterns", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("url_categories")
    op.drop_table("url_filter_rules")
