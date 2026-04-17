"""Add FERPA compliance tables.

Revision ID: 054
Revises: 053
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("ferpa_educational_records"):
        op.create_table(
            "ferpa_educational_records",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("group_id", sa.Uuid(), nullable=False),
            sa.Column("member_id", sa.Uuid(), nullable=False),
            sa.Column("record_type", sa.String(50), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_directory_info", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("classification", sa.String(30), nullable=False, server_default="protected"),
            sa.Column("created_by", sa.Uuid(), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["member_id"], ["group_members.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ferpa_educational_records_group_id", "ferpa_educational_records", ["group_id"])
        op.create_index("ix_ferpa_educational_records_member_id", "ferpa_educational_records", ["member_id"])

    if not table_exists("ferpa_access_logs"):
        op.create_table(
            "ferpa_access_logs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("group_id", sa.Uuid(), nullable=False),
            sa.Column("record_id", sa.Uuid(), nullable=False),
            sa.Column("accessor_user_id", sa.Uuid(), nullable=False),
            sa.Column("access_type", sa.String(30), nullable=False),
            sa.Column("purpose", sa.String(500), nullable=False),
            sa.Column("legitimate_interest", sa.String(100), nullable=True),
            sa.Column("accessed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["record_id"], ["ferpa_educational_records.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["accessor_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ferpa_access_logs_group_id", "ferpa_access_logs", ["group_id"])
        op.create_index("ix_ferpa_access_logs_record_id", "ferpa_access_logs", ["record_id"])
        op.create_index("ix_ferpa_access_logs_accessor_user_id", "ferpa_access_logs", ["accessor_user_id"])

    if not table_exists("ferpa_annual_notifications"):
        op.create_table(
            "ferpa_annual_notifications",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("group_id", sa.Uuid(), nullable=False),
            sa.Column("school_year", sa.String(9), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("template_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("recipient_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("notification_method", sa.String(30), nullable=False, server_default="email"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ferpa_annual_notifications_group_id", "ferpa_annual_notifications", ["group_id"])

    if not table_exists("ferpa_data_sharing_agreements"):
        op.create_table(
            "ferpa_data_sharing_agreements",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("group_id", sa.Uuid(), nullable=False),
            sa.Column("third_party_name", sa.String(255), nullable=False),
            sa.Column("purpose", sa.String(500), nullable=False),
            sa.Column("data_elements", sa.JSON(), nullable=False),
            sa.Column("legal_basis", sa.String(50), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("effective_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expiration_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.Uuid(), nullable=False),
            sa.Column("terms", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ferpa_data_sharing_agreements_group_id", "ferpa_data_sharing_agreements", ["group_id"])


def downgrade() -> None:
    op.drop_table("ferpa_data_sharing_agreements")
    op.drop_table("ferpa_annual_notifications")
    op.drop_table("ferpa_access_logs")
    op.drop_table("ferpa_educational_records")
