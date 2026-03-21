"""Add description column to content_reports table.

Revision ID: 041
Revises: 040
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from migration_helpers import column_exists

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not column_exists("content_reports", "description"):
        op.add_column(
            "content_reports",
            sa.Column("description", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    if column_exists("content_reports", "description"):
        op.drop_column("content_reports", "description")
