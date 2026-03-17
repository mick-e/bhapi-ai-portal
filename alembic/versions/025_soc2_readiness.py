"""Add audit_logs and incident_records tables for SOC 2.

Revision ID: 025
Revises: 024
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None

def upgrade() -> None:
    if not table_exists("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("actor_email", sa.String(255), nullable=True),
            sa.Column("action", sa.String(100), nullable=False, index=True),
            sa.Column("resource_type", sa.String(100), nullable=False),
            sa.Column("resource_id", sa.String(255), nullable=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("user_agent", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not table_exists("incident_records"):
        op.create_table(
            "incident_records",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("category", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("reported_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("resolution", sa.Text(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("root_cause", sa.Text(), nullable=True),
            sa.Column("timeline", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

def downgrade() -> None:
    op.drop_table("incident_records")
    op.drop_table("audit_logs")
