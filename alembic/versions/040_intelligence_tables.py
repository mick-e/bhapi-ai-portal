"""Intelligence tables — social graph edges, abuse signals, behavioral baselines.

Revision ID: 040
Revises: 039
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from migration_helpers import table_exists

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Social graph edges table
    if not table_exists("social_graph_edges"):
        op.create_table(
            "social_graph_edges",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("source_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("target_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("edge_type", sa.String(20), nullable=False),
            sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("last_interaction", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_social_graph_edges_source_id", "social_graph_edges", ["source_id"])
        op.create_index("ix_social_graph_edges_target_id", "social_graph_edges", ["target_id"])
        op.create_index("ix_social_graph_source_target", "social_graph_edges", ["source_id", "target_id"])
        op.create_index("ix_social_graph_source_type", "social_graph_edges", ["source_id", "edge_type"])

    # Abuse signals table
    if not table_exists("abuse_signals"):
        op.create_table(
            "abuse_signals",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("signal_type", sa.String(30), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolved_by", sa.Uuid(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_abuse_signals_member_id", "abuse_signals", ["member_id"])
        op.create_index("ix_abuse_signals_member_type", "abuse_signals", ["member_id", "signal_type"])
        op.create_index("ix_abuse_signals_severity", "abuse_signals", ["severity"])

    # Behavioral baselines table
    if not table_exists("behavioral_baselines"):
        op.create_table(
            "behavioral_baselines",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("window_days", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("metrics", sa.JSON(), nullable=True),
            sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_behavioral_baselines_member_id", "behavioral_baselines", ["member_id"])
        op.create_index("ix_behavioral_baselines_member_window", "behavioral_baselines", ["member_id", "window_days"])


def downgrade() -> None:
    op.drop_table("behavioral_baselines")
    op.drop_table("abuse_signals")
    op.drop_table("social_graph_edges")
