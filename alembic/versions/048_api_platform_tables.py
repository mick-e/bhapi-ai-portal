"""Create API platform tables — OAuth clients, tokens, tiers, webhooks, usage.

Revision ID: 048
Revises: 044
Create Date: 2026-03-23
"""

import uuid as _uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "048"
down_revision = "046"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Tier seed data
# ---------------------------------------------------------------------------

TIER_SEEDS = [
    {"name": "school", "rate_limit_per_hour": 1000, "max_webhooks": 10, "price_monthly": None},
    {"name": "partner", "rate_limit_per_hour": 5000, "max_webhooks": 50, "price_monthly": 99.0},
    {"name": "enterprise", "rate_limit_per_hour": 10000, "max_webhooks": 999, "price_monthly": None},
]


def upgrade() -> None:
    # ------------------------------------------------------------------
    # oauth_clients
    # ------------------------------------------------------------------
    op.create_table(
        "oauth_clients",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("client_id", sa.String(64), nullable=False, unique=True),
        sa.Column("client_secret_hash", sa.String(255), nullable=False),
        sa.Column("redirect_uris", sa.JSON(), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False, server_default="school"),
        sa.Column("owner_id", PG_UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
    op.create_index("ix_oauth_clients_client_id", "oauth_clients", ["client_id"], unique=True)

    # ------------------------------------------------------------------
    # oauth_tokens
    # ------------------------------------------------------------------
    op.create_table(
        "oauth_tokens",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "client_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("access_token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("refresh_token_hash", sa.String(255), nullable=True, unique=True),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
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
    op.create_index("ix_oauth_tokens_client_id", "oauth_tokens", ["client_id"])
    op.create_index(
        "ix_oauth_tokens_access_token_hash", "oauth_tokens", ["access_token_hash"], unique=True,
    )

    # ------------------------------------------------------------------
    # api_key_tiers
    # ------------------------------------------------------------------
    op.create_table(
        "api_key_tiers",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(20), nullable=False, unique=True),
        sa.Column("rate_limit_per_hour", sa.Integer(), nullable=False),
        sa.Column("max_webhooks", sa.Integer(), nullable=False),
        sa.Column("price_monthly", sa.Float(), nullable=True),
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
    op.create_index("ix_api_key_tiers_name", "api_key_tiers", ["name"], unique=True)

    # ------------------------------------------------------------------
    # platform_webhook_endpoints
    # ------------------------------------------------------------------
    op.create_table(
        "platform_webhook_endpoints",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "client_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("secret_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        "ix_platform_webhook_endpoints_client_id",
        "platform_webhook_endpoints",
        ["client_id"],
    )

    # ------------------------------------------------------------------
    # platform_webhook_deliveries
    # ------------------------------------------------------------------
    op.create_table(
        "platform_webhook_deliveries",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "endpoint_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("platform_webhook_endpoints.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("delivered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error", sa.Text(), nullable=True),
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
        "ix_platform_wh_deliveries_endpoint_created",
        "platform_webhook_deliveries",
        ["endpoint_id", "created_at"],
    )

    # ------------------------------------------------------------------
    # api_usage_records
    # ------------------------------------------------------------------
    op.create_table(
        "api_usage_records",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "client_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("webhook_deliveries", sa.Integer(), nullable=False, server_default="0"),
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
        "ix_api_usage_client_date",
        "api_usage_records",
        ["client_id", "date"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # Seed tier configs
    # ------------------------------------------------------------------
    tier_table = sa.table(
        "api_key_tiers",
        sa.column("id", PG_UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("rate_limit_per_hour", sa.Integer),
        sa.column("max_webhooks", sa.Integer),
        sa.column("price_monthly", sa.Float),
    )
    conn = op.get_bind()
    for tier in TIER_SEEDS:
        existing = conn.execute(
            sa.select(tier_table.c.name).where(tier_table.c.name == tier["name"])
        ).fetchone()
        if not existing:
            conn.execute(
                tier_table.insert().values(
                    id=_uuid.uuid4(),
                    name=tier["name"],
                    rate_limit_per_hour=tier["rate_limit_per_hour"],
                    max_webhooks=tier["max_webhooks"],
                    price_monthly=tier["price_monthly"],
                )
            )


def downgrade() -> None:
    op.drop_index("ix_api_usage_client_date", table_name="api_usage_records")
    op.drop_table("api_usage_records")

    op.drop_index(
        "ix_platform_wh_deliveries_endpoint_created",
        table_name="platform_webhook_deliveries",
    )
    op.drop_table("platform_webhook_deliveries")

    op.drop_index(
        "ix_platform_webhook_endpoints_client_id",
        table_name="platform_webhook_endpoints",
    )
    op.drop_table("platform_webhook_endpoints")

    op.drop_index("ix_api_key_tiers_name", table_name="api_key_tiers")
    op.drop_table("api_key_tiers")

    op.drop_index(
        "ix_oauth_tokens_access_token_hash", table_name="oauth_tokens",
    )
    op.drop_index("ix_oauth_tokens_client_id", table_name="oauth_tokens")
    op.drop_table("oauth_tokens")

    op.drop_index("ix_oauth_clients_client_id", table_name="oauth_clients")
    op.drop_table("oauth_clients")
