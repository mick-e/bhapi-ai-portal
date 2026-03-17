"""Add free tier support columns to subscriptions.

Revision ID: 018
Revises: 017
Create Date: 2026-03-17

Adds platform_limit and feature_flags columns to subscriptions table
for free tier feature gating.
"""

from alembic import op
import sqlalchemy as sa

from migration_helpers import column_exists

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not column_exists("subscriptions", "platform_limit"):
        op.add_column(
            "subscriptions",
            sa.Column("platform_limit", sa.Integer(), nullable=True),
        )

    if not column_exists("subscriptions", "feature_flags"):
        op.add_column(
            "subscriptions",
            sa.Column("feature_flags", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("subscriptions", "feature_flags")
    op.drop_column("subscriptions", "platform_limit")
