"""Add push_subscriptions table for web push notifications.

Revision ID: 020
Revises: 019
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None

def upgrade() -> None:
    if not table_exists("push_subscriptions"):
        op.create_table(
            "push_subscriptions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("endpoint", sa.Text(), nullable=False),
            sa.Column("p256dh_key", sa.String(255), nullable=False),
            sa.Column("auth_key", sa.String(255), nullable=False),
            sa.Column("user_agent", sa.String(500), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

def downgrade() -> None:
    op.drop_table("push_subscriptions")
