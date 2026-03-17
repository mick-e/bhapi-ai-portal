"""Add developer portal and marketplace tables.

Revision ID: 027
Revises: 026
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None

def upgrade() -> None:
    if not table_exists("developer_apps"):
        op.create_table(
            "developer_apps",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("client_id", sa.String(255), unique=True, nullable=False),
            sa.Column("client_secret_hash", sa.String(255), nullable=False),
            sa.Column("redirect_uris", sa.JSON(), nullable=True),
            sa.Column("scopes", sa.JSON(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("approved", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not table_exists("webhook_endpoints"):
        op.create_table(
            "webhook_endpoints",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("app_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("url", sa.Text(), nullable=False),
            sa.Column("events", sa.JSON(), nullable=True),
            sa.Column("secret_hash", sa.String(255), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not table_exists("webhook_deliveries"):
        op.create_table(
            "webhook_deliveries",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("endpoint_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("event_type", sa.String(100), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("status_code", sa.Integer(), nullable=True),
            sa.Column("response_body", sa.Text(), nullable=True),
            sa.Column("success", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not table_exists("marketplace_modules"):
        op.create_table(
            "marketplace_modules",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("developer_app_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("slug", sa.String(100), unique=True, nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category", sa.String(100), nullable=False),
            sa.Column("version", sa.String(20), nullable=False),
            sa.Column("icon_url", sa.String(500), nullable=True),
            sa.Column("install_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rating", sa.Float(), nullable=True),
            sa.Column("published", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not table_exists("installed_modules"):
        op.create_table(
            "installed_modules",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("module_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("config", sa.JSON(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

def downgrade() -> None:
    op.drop_table("installed_modules")
    op.drop_table("marketplace_modules")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_endpoints")
    op.drop_table("developer_apps")
