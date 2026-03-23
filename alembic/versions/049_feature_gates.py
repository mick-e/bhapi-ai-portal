"""Create feature_gates table and seed default gates.

Revision ID: 049
Revises: 044
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid as _uuid
from migration_helpers import table_exists

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Default feature gates seeded on upgrade
# ---------------------------------------------------------------------------

DEFAULT_GATES = [
    {
        "feature_key": "location_tracking",
        "required_tier": "family_plus",
        "description": "Real-time location tracking for children",
    },
    {
        "feature_key": "screen_time",
        "required_tier": "family_plus",
        "description": "Screen time monitoring and limits",
    },
    {
        "feature_key": "creative_tools",
        "required_tier": "family_plus",
        "description": "AI creative tools (art, story generation)",
    },
    {
        "feature_key": "api_access",
        "required_tier": "school",
        "description": "Programmatic API access for third-party integrations",
    },
    {
        "feature_key": "unified_dashboard",
        "required_tier": "family",
        "description": "Unified parent dashboard across Safety + Social apps",
    },
    {
        "feature_key": "real_time_alerts",
        "required_tier": "family",
        "description": "Real-time push/SMS alerts for safety events",
    },
    {
        "feature_key": "blocking",
        "required_tier": "family",
        "description": "AI platform blocking and content filtering",
    },
    {
        "feature_key": "reports",
        "required_tier": "family",
        "description": "PDF and CSV report generation",
    },
    {
        "feature_key": "social_access",
        "required_tier": "family",
        "description": "Access to Bhapi Social safe social network",
    },
]


def upgrade() -> None:
    if not table_exists("feature_gates"):
        op.create_table(
            "feature_gates",
            sa.Column(
                "id",
                PG_UUID(as_uuid=True),
                primary_key=True,
                default=_uuid.uuid4,
                nullable=False,
            ),
            sa.Column("feature_key", sa.String(50), nullable=False, unique=True),
            sa.Column("required_tier", sa.String(20), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
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
            "ix_feature_gates_feature_key",
            "feature_gates",
            ["feature_key"],
            unique=True,
        )

    # Seed default gates
    feature_gates_table = sa.table(
        "feature_gates",
        sa.column("id", PG_UUID(as_uuid=True)),
        sa.column("feature_key", sa.String),
        sa.column("required_tier", sa.String),
        sa.column("description", sa.String),
    )

    conn = op.get_bind()
    for gate in DEFAULT_GATES:
        # Upsert-style: skip if feature_key already exists
        existing = conn.execute(
            sa.select(feature_gates_table.c.feature_key).where(
                feature_gates_table.c.feature_key == gate["feature_key"]
            )
        ).fetchone()
        if not existing:
            conn.execute(
                feature_gates_table.insert().values(
                    id=_uuid.uuid4(),
                    feature_key=gate["feature_key"],
                    required_tier=gate["required_tier"],
                    description=gate["description"],
                )
            )


def downgrade() -> None:
    op.drop_index("ix_feature_gates_feature_key", table_name="feature_gates")
    op.drop_table("feature_gates")
