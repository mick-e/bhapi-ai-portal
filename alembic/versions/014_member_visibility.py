"""Add member visibility and child self-view tables.

Revision ID: 014
Revises: 009
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "014"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. member_visibility table
    op.create_table(
        "member_visibility",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("group_members.id"), nullable=False),
        sa.Column("visible_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_member_visibility_group_id", "member_visibility", ["group_id"])
    op.create_index("ix_member_visibility_member_id", "member_visibility", ["member_id"])
    op.create_index(
        "ix_member_visibility_group_member",
        "member_visibility",
        ["group_id", "member_id"],
    )

    # 2. child_self_views table
    op.create_table(
        "child_self_views",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("group_members.id"), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sections", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_child_self_views_group_id", "child_self_views", ["group_id"])
    op.create_index("ix_child_self_views_member_id", "child_self_views", ["member_id"])

    # 3. Add device_id nullable FK to capture_events
    op.add_column(
        "capture_events",
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("device_registrations.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_capture_events_device_id", "capture_events", ["device_id"])


def downgrade() -> None:
    op.drop_index("ix_capture_events_device_id", table_name="capture_events")
    op.drop_column("capture_events", "device_id")
    op.drop_table("child_self_views")
    op.drop_table("member_visibility")
