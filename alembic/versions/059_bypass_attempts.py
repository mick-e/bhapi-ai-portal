"""Bypass attempts table for VPN/proxy/incognito/tampering detection.

Phase 4 Task 23 (R-24).

Revision ID: 059
Revises: 058
Create Date: 2026-04-18
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from migration_helpers import table_exists

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("bypass_attempts"):
        op.create_table(
            "bypass_attempts",
            sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column(
                "group_id",
                PG_UUID(as_uuid=True),
                sa.ForeignKey("groups.id"),
                nullable=False,
            ),
            sa.Column(
                "member_id",
                PG_UUID(as_uuid=True),
                sa.ForeignKey("group_members.id"),
                nullable=False,
            ),
            sa.Column("bypass_type", sa.String(32), nullable=False),
            sa.Column("detection_signals", sa.JSON, nullable=True),
            sa.Column("user_agent", sa.String(500), nullable=True),
            sa.Column(
                "auto_blocked",
                sa.Boolean,
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_bypass_attempts_group_id",
            "bypass_attempts",
            ["group_id"],
        )
        op.create_index(
            "ix_bypass_attempts_member_id",
            "bypass_attempts",
            ["member_id"],
        )
        op.create_index(
            "ix_bypass_attempts_member_created",
            "bypass_attempts",
            ["member_id", "created_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_bypass_attempts_member_created", table_name="bypass_attempts")
    op.drop_index("ix_bypass_attempts_member_id", table_name="bypass_attempts")
    op.drop_index("ix_bypass_attempts_group_id", table_name="bypass_attempts")
    op.drop_table("bypass_attempts")
