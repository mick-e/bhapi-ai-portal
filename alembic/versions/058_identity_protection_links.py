"""Identity protection partner links — Phase 4 Task 22.

Stores per-user link to an external identity-protection partner account
(Aura, IDX, LifeLock, etc.) with the consent text version they accepted.

Revision ID: 058
Revises: 057
Create Date: 2026-04-18
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from migration_helpers import table_exists

revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not table_exists("identity_protection_links"):
        op.create_table(
            "identity_protection_links",
            sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column(
                "user_id",
                PG_UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=False,
                unique=True,
            ),
            sa.Column("partner_name", sa.String(64), nullable=False),
            sa.Column("partner_account_id", sa.String(128), nullable=False),
            sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consent_text_version", sa.String(32), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="active"),
            sa.Column("last_alert_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata_json", sa.JSON, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_identity_protection_links_user_id",
            "identity_protection_links",
            ["user_id"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_protection_links_user_id",
        table_name="identity_protection_links",
    )
    op.drop_table("identity_protection_links")
