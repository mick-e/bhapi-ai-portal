"""Add intelligence network tables for anonymized threat signal sharing.

Revision ID: 056
Revises: 055
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa
from migration_helpers import table_exists

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Anonymized threat signals
    if not table_exists("intel_network_threat_signals"):
        op.create_table(
            "intel_network_threat_signals",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("signal_type", sa.String(100), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("pattern_data", sa.JSON(), nullable=False),
            sa.Column("sample_size", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("contributor_region", sa.String(50), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("feedback_helpful", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("feedback_false_positive", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_intel_threat_signals_type", "intel_network_threat_signals", ["signal_type"])
        op.create_index("ix_intel_threat_signals_severity", "intel_network_threat_signals", ["severity"])

    # Group subscriptions
    if not table_exists("intel_network_subscriptions"):
        op.create_table(
            "intel_network_subscriptions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("group_id", sa.Uuid(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("signal_types", sa.JSON(), nullable=False),
            sa.Column("minimum_severity", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_intel_subscriptions_group_id", "intel_network_subscriptions", ["group_id"], unique=True)

    # Signal delivery audit
    if not table_exists("intel_network_signal_deliveries"):
        op.create_table(
            "intel_network_signal_deliveries",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("signal_id", sa.Uuid(), nullable=False),
            sa.Column("group_id", sa.Uuid(), nullable=False),
            sa.Column("delivered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_intel_deliveries_signal_id", "intel_network_signal_deliveries", ["signal_id"])
        op.create_index("ix_intel_deliveries_group_id", "intel_network_signal_deliveries", ["group_id"])

    # Anonymization audit trail
    if not table_exists("intel_network_anonymization_audit"):
        op.create_table(
            "intel_network_anonymization_audit",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("signal_id", sa.Uuid(), nullable=False),
            sa.Column("source_group_id", sa.Uuid(), nullable=False),
            sa.Column("fields_stripped", sa.JSON(), nullable=False),
            sa.Column("k_anonymity_applied", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("dp_noise_applied", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("anonymized_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_intel_anon_audit_signal_id", "intel_network_anonymization_audit", ["signal_id"])


def downgrade() -> None:
    op.drop_table("intel_network_anonymization_audit")
    op.drop_table("intel_network_signal_deliveries")
    op.drop_table("intel_network_subscriptions")
    op.drop_table("intel_network_threat_signals")
