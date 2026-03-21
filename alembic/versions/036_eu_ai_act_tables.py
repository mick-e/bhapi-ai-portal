"""EU AI Act conformity assessment, tech docs, risk management, bias testing.

Revision ID: 036
Revises: 035
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from migration_helpers import table_exists

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Conformity assessment table
    if not table_exists("eu_ai_act_conformity_assessments"):
        op.create_table(
            "eu_ai_act_conformity_assessments",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("group_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("version", sa.Integer(), nullable=False, default=1),
            sa.Column("status", sa.String(20), nullable=False, default="draft"),
            sa.Column("sections", sa.JSON(), nullable=False),
            sa.Column("assessor", sa.String(200), nullable=False),
            sa.Column("assessed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # Technical documentation table
    if not table_exists("eu_ai_act_technical_docs"):
        op.create_table(
            "eu_ai_act_technical_docs",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("group_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("version", sa.Integer(), nullable=False, default=1),
            sa.Column("sections", sa.JSON(), nullable=False),
            sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # Risk management records table
    if not table_exists("eu_ai_act_risk_management"):
        op.create_table(
            "eu_ai_act_risk_management",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("group_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("risk_type", sa.String(50), nullable=False),
            sa.Column("description", sa.String(2000), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("likelihood", sa.String(20), nullable=False),
            sa.Column("mitigation", sa.String(2000), nullable=False),
            sa.Column("residual_risk", sa.String(20), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # Bias test results table
    if not table_exists("eu_ai_act_bias_tests"):
        op.create_table(
            "eu_ai_act_bias_tests",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("group_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("model_id", sa.String(200), nullable=False),
            sa.Column("test_data_hash", sa.String(64), nullable=False),
            sa.Column("results", sa.JSON(), nullable=False),
            sa.Column("overall_score", sa.Float(), nullable=False),
            sa.Column("tested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("eu_ai_act_bias_tests")
    op.drop_table("eu_ai_act_risk_management")
    op.drop_table("eu_ai_act_technical_docs")
    op.drop_table("eu_ai_act_conformity_assessments")
