"""Add demo_sessions table for enterprise sales enablement.

Revision ID: 019
Revises: 018
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from migration_helpers import table_exists

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("demo_sessions"):
        op.create_table(
            "demo_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("organisation", sa.String(255), nullable=False),
            sa.Column("account_type", sa.String(20), nullable=False),
            sa.Column("demo_token", sa.String(255), unique=True, nullable=False, index=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("demo_data", sa.JSON(), nullable=True),
            sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("demo_sessions")
