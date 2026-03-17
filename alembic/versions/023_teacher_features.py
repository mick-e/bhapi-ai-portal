"""Add parent_teacher_notes table.

Revision ID: 022
Revises: 021
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None

def upgrade() -> None:
    if not table_exists("parent_teacher_notes"):
        op.create_table(
            "parent_teacher_notes",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("author_role", sa.String(20), nullable=False),
            sa.Column("subject", sa.String(255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reply_to_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

def downgrade() -> None:
    op.drop_table("parent_teacher_notes")
