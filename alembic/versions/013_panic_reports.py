"""Add panic reports table for child panic button feature.

Revision ID: 013
Revises: 012
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "panic_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("group_members.id"), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("message", sa.String(500), nullable=True),
        sa.Column("platform", sa.String(100), nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("parent_response", sa.String(500), nullable=True),
        sa.Column("parent_responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_panic_reports_group_id", "panic_reports", ["group_id"])
    op.create_index("ix_panic_reports_member_id", "panic_reports", ["member_id"])
    op.create_index("ix_panic_reports_group_created", "panic_reports", ["group_id", "created_at"])


def downgrade() -> None:
    op.drop_table("panic_reports")
