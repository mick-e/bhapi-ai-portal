"""Add cross-product tables.

Revision ID: 026
Revises: 025
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None

def upgrade() -> None:
    if not table_exists("product_registrations"):
        op.create_table(
            "product_registrations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("product_name", sa.String(100), nullable=False),
            sa.Column("product_type", sa.String(50), nullable=False),
            sa.Column("api_key_hash", sa.String(255), nullable=False, unique=True),
            sa.Column("owner_group_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("permissions", sa.JSON(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not table_exists("shared_profiles"):
        op.create_table(
            "shared_profiles",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("profile_data", sa.JSON(), nullable=True),
            sa.Column("sync_status", sa.String(20), nullable=False, server_default="synced"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not table_exists("cross_product_alerts"):
        op.create_table(
            "cross_product_alerts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("source_product", sa.String(50), nullable=False),
            sa.Column("alert_type", sa.String(100), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

def downgrade() -> None:
    op.drop_table("cross_product_alerts")
    op.drop_table("shared_profiles")
    op.drop_table("product_registrations")
