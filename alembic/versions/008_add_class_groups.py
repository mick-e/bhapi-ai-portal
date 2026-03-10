"""Add class_groups and class_group_members tables for school admin dashboard.

Revision ID: 008
Revises: 007
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. class_groups table
    op.create_table(
        "class_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("grade_level", sa.String(50), nullable=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("academic_year", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_class_groups_group_id", "class_groups", ["group_id"])

    # 2. class_group_members table
    op.create_table(
        "class_group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("class_group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("class_groups.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("group_members.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_class_group_members_class_group_id", "class_group_members", ["class_group_id"])
    op.create_index("ix_class_group_members_member_id", "class_group_members", ["member_id"])


def downgrade() -> None:
    op.drop_table("class_group_members")
    op.drop_table("class_groups")
