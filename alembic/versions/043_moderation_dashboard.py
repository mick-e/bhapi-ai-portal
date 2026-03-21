"""Add moderation dashboard tables: moderator_assignments, sla_metrics, pattern_detections.

Revision ID: 043
Revises: 042
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from migration_helpers import table_exists

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("moderator_assignments"):
        op.create_table(
            "moderator_assignments",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("queue_id", UUID(as_uuid=True), sa.ForeignKey("moderation_queue.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("moderator_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="assigned"),
            sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if not table_exists("sla_metrics"):
        op.create_table(
            "sla_metrics",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("pipeline", sa.String(20), nullable=False, index=True),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
            sa.Column("p95_ms", sa.Float, nullable=False, server_default="0"),
            sa.Column("items_total", sa.Integer, nullable=False, server_default="0"),
            sa.Column("items_in_sla", sa.Integer, nullable=False, server_default="0"),
            sa.Column("items_breached_sla", sa.Integer, nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if not table_exists("pattern_detections"):
        op.create_table(
            "pattern_detections",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("pattern_type", sa.String(50), nullable=False, index=True),
            sa.Column("description", sa.Text, nullable=False),
            sa.Column("severity", sa.String(20), nullable=False, server_default="low"),
            sa.Column("details", sa.JSON, nullable=True),
            sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
            sa.Column("acknowledged", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("pattern_detections")
    op.drop_table("sla_metrics")
    op.drop_table("moderator_assignments")
