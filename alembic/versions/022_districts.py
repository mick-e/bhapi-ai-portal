"""Add districts and district_schools tables.

Revision ID: 021
Revises: 020
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None

def upgrade() -> None:
    if not table_exists("districts"):
        op.create_table(
            "districts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("code", sa.String(50), unique=True, nullable=True),
            sa.Column("admin_email", sa.String(255), nullable=False),
            sa.Column("state", sa.String(100), nullable=True),
            sa.Column("country", sa.String(100), nullable=False, server_default="US"),
            sa.Column("settings", sa.JSON(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if not table_exists("district_schools"):
        op.create_table(
            "district_schools",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("district_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
            sa.Column("school_name", sa.String(255), nullable=False),
            sa.Column("pilot_status", sa.String(20), nullable=False, server_default="pilot"),
            sa.Column("student_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

def downgrade() -> None:
    op.drop_table("district_schools")
    op.drop_table("districts")
