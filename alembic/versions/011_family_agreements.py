"""Add family_agreements table.

Revision ID: 011
Revises: 010
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from migration_helpers import table_exists, index_exists

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("family_agreements"):
        op.create_table(
            "family_agreements",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("template_id", sa.String(50), nullable=False),
            sa.Column("rules", sa.JSON(), nullable=True),
            sa.Column("signed_by_parent", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("signed_by_parent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("signed_by_members", sa.JSON(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("review_due", sa.Date(), nullable=False),
            sa.Column("last_reviewed", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
    if not index_exists("family_agreements", "ix_family_agreements_group_id"):
        op.create_index("ix_family_agreements_group_id", "family_agreements", ["group_id"])
    if not index_exists("family_agreements", "ix_family_agreements_active"):
        op.create_index("ix_family_agreements_active", "family_agreements", ["group_id", "active"])


def downgrade() -> None:
    op.drop_table("family_agreements")
