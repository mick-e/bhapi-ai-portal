"""Add emergency_contacts table.

Revision ID: 016
Revises: 015
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from migration_helpers import table_exists, index_exists

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("emergency_contacts"):
        op.create_table(
            "emergency_contacts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("relationship", sa.String(100), nullable=False),
            sa.Column("phone", sa.String(20), nullable=True),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("notify_on", sa.JSON(), nullable=True),
            sa.Column("consent_given", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
    if not index_exists("emergency_contacts", "ix_emergency_contacts_group_id"):
        op.create_index("ix_emergency_contacts_group_id", "emergency_contacts", ["group_id"])


def downgrade() -> None:
    op.drop_table("emergency_contacts")
