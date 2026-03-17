"""Add onboarding_progress table.

Revision ID: 020
Revises: 019
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None

def upgrade() -> None:
    if not table_exists("onboarding_progress"):
        op.create_table(
            "onboarding_progress",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completed_steps", sa.JSON(), nullable=True),
            sa.Column("dismissed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

def downgrade() -> None:
    op.drop_table("onboarding_progress")
