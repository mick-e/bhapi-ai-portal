"""UK AADC gap analysis and privacy-by-default tables.

Revision ID: 038
Revises: 036
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from migration_helpers import table_exists

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # AADC assessment table
    if not table_exists("aadc_assessments"):
        op.create_table(
            "aadc_assessments",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("group_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("version", sa.Integer(), nullable=False, default=1),
            sa.Column("standards", sa.JSON(), nullable=False),
            sa.Column("assessed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("assessor", sa.String(200), nullable=False),
            sa.Column("score", sa.Float(), nullable=False, default=0.0),
            sa.Column("overall_status", sa.String(20), nullable=False, default="non_compliant"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # Privacy defaults table
    if not table_exists("aadc_privacy_defaults"):
        op.create_table(
            "aadc_privacy_defaults",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("user_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("age_tier", sa.String(20), nullable=False),
            sa.Column("settings", sa.JSON(), nullable=False),
            sa.Column("effective_from", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_by", sa.String(200), nullable=False, default="system"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("aadc_privacy_defaults")
    op.drop_table("aadc_assessments")
