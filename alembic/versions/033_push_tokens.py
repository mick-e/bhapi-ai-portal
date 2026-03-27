"""Push tokens table for Expo mobile push notifications.

Revision ID: 033
Revises: 032
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from migration_helpers import table_exists

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("push_tokens"):
        op.create_table(
            "push_tokens",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("token", sa.String(255), nullable=False, unique=True),
            sa.Column("device_type", sa.String(20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("push_tokens")
