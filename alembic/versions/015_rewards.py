"""Add rewards table.

Revision ID: 015
Revises: 014
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rewards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("group_members.id"), nullable=False),
        sa.Column("reward_type", sa.String(50), nullable=False),
        sa.Column("trigger", sa.String(100), nullable=False),
        sa.Column("trigger_description", sa.String(255), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_rewards_group_id", "rewards", ["group_id"])
    op.create_index("ix_rewards_member_id", "rewards", ["member_id"])
    op.create_index("ix_rewards_group_member", "rewards", ["group_id", "member_id"])


def downgrade() -> None:
    op.drop_table("rewards")
