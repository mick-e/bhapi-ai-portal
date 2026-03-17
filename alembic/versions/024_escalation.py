"""Add escalation_partners and escalation_records tables.

Revision ID: 023
Revises: 022
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None

def upgrade() -> None:
    if not table_exists("escalation_partners"):
        op.create_table(
            "escalation_partners",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("provider_type", sa.String(50), nullable=False),
            sa.Column("webhook_url", sa.Text(), nullable=True),
            sa.Column("contact_email", sa.String(255), nullable=True),
            sa.Column("contact_phone", sa.String(50), nullable=True),
            sa.Column("severity_threshold", sa.String(20), nullable=False, server_default="critical"),
            sa.Column("categories", sa.JSON(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not table_exists("escalation_records"):
        op.create_table(
            "escalation_records",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("category", sa.String(100), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("response_notes", sa.Text(), nullable=True),
            sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

def downgrade() -> None:
    op.drop_table("escalation_records")
    op.drop_table("escalation_partners")
