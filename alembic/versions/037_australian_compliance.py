"""Australian Online Safety compliance — age verification, eSafety reports, cyberbullying cases.

Revision ID: 037
Revises: 036
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from migration_helpers import table_exists

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # AU age verification records
    if not table_exists("au_age_verification_records"):
        op.create_table(
            "au_age_verification_records",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("country_code", sa.String(2), nullable=False, server_default="AU"),
            sa.Column("method", sa.String(50), nullable=False),
            sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verification_data", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # AU eSafety Commissioner reports
    if not table_exists("au_esafety_reports"):
        op.create_table(
            "au_esafety_reports",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("content_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("content_type", sa.String(50), nullable=False),
            sa.Column("group_id", sa.Uuid(), nullable=True, index=True),
            sa.Column("reported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("actioned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("sla_hours", sa.Integer(), nullable=False, server_default=sa.text("24")),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("action_taken", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # AU cyberbullying cases
    if not table_exists("au_cyberbullying_cases"):
        op.create_table(
            "au_cyberbullying_cases",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("reporter_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("target_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("group_id", sa.Uuid(), nullable=True, index=True),
            sa.Column("evidence_ids", sa.JSON(), nullable=True),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("workflow_steps", sa.JSON(), nullable=True),
            sa.Column("resolution", sa.String(500), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("au_cyberbullying_cases")
    op.drop_table("au_esafety_reports")
    op.drop_table("au_age_verification_records")
