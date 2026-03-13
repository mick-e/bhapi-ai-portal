"""Add AI Literacy Assessment tables.

Revision ID: 009
Revises: 008
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from migration_helpers import table_exists, index_exists

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. literacy_modules table
    if not table_exists("literacy_modules"):
        op.create_table(
            "literacy_modules",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.String(2000), nullable=False),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column("difficulty_level", sa.String(20), nullable=False),
            sa.Column("min_age", sa.Integer(), nullable=False, server_default="6"),
            sa.Column("max_age", sa.Integer(), nullable=False, server_default="18"),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
    if not index_exists("literacy_modules", "ix_literacy_modules_category"):
        op.create_index("ix_literacy_modules_category", "literacy_modules", ["category"])

    # 2. literacy_questions table
    if not table_exists("literacy_questions"):
        op.create_table(
            "literacy_questions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("module_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("literacy_modules.id"), nullable=False),
            sa.Column("question_text", sa.String(1000), nullable=False),
            sa.Column("question_type", sa.String(20), nullable=False),
            sa.Column("options", sa.JSON(), nullable=False),
            sa.Column("correct_answer", sa.String(255), nullable=False),
            sa.Column("explanation", sa.String(2000), nullable=False),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
    if not index_exists("literacy_questions", "ix_literacy_questions_module_id"):
        op.create_index("ix_literacy_questions_module_id", "literacy_questions", ["module_id"])

    # 3. literacy_assessments table
    if not table_exists("literacy_assessments"):
        op.create_table(
            "literacy_assessments",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("group_members.id"), nullable=False),
            sa.Column("module_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("literacy_modules.id"), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("answers", sa.JSON(), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
    if not index_exists("literacy_assessments", "ix_literacy_assessments_group_id"):
        op.create_index("ix_literacy_assessments_group_id", "literacy_assessments", ["group_id"])
    if not index_exists("literacy_assessments", "ix_literacy_assessments_member_id"):
        op.create_index("ix_literacy_assessments_member_id", "literacy_assessments", ["member_id"])
    if not index_exists("literacy_assessments", "ix_literacy_assessments_module_id"):
        op.create_index("ix_literacy_assessments_module_id", "literacy_assessments", ["module_id"])

    # 4. literacy_progress table
    if not table_exists("literacy_progress"):
        op.create_table(
            "literacy_progress",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("group_members.id"), nullable=False),
            sa.Column("modules_completed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("current_level", sa.String(20), nullable=False, server_default="beginner"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
    if not index_exists("literacy_progress", "ix_literacy_progress_group_id"):
        op.create_index("ix_literacy_progress_group_id", "literacy_progress", ["group_id"])
    if not index_exists("literacy_progress", "ix_literacy_progress_member_id"):
        op.create_index("ix_literacy_progress_member_id", "literacy_progress", ["member_id"])


def downgrade() -> None:
    op.drop_table("literacy_progress")
    op.drop_table("literacy_assessments")
    op.drop_table("literacy_questions")
    op.drop_table("literacy_modules")
