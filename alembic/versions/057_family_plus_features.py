"""Seed Family+ feature gates — Phase 4 Task 21.

Revision ID: 057
Revises: 056
Create Date: 2026-04-17
"""
import uuid as _uuid

import sqlalchemy as sa
from alembic import op

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


FAMILY_PLUS_GATES = [
    {
        "feature_key": "identity_protection_partner",
        "required_tier": "family_plus",
        "description": "Bundled identity protection via partner integration (Family+ exclusive)",
    },
    {
        "feature_key": "intel_network_signals",
        "required_tier": "family_plus",
        "description": "Cross-customer anonymized threat signals (Family+ and above)",
    },
    {
        "feature_key": "priority_support",
        "required_tier": "family_plus",
        "description": "Priority email + chat support with <24h SLA",
    },
    {
        "feature_key": "screen_time_management",
        "required_tier": "family_plus",
        "description": "Screen time limits and scheduling (alias for existing 'screen_time' gate)",
    },
]


def upgrade() -> None:
    feature_gates_table = sa.table(
        "feature_gates",
        sa.column("id", sa.String),
        sa.column("feature_key", sa.String),
        sa.column("required_tier", sa.String),
        sa.column("description", sa.String),
    )

    conn = op.get_bind()
    for gate in FAMILY_PLUS_GATES:
        existing = conn.execute(
            sa.select(feature_gates_table.c.feature_key).where(
                feature_gates_table.c.feature_key == gate["feature_key"]
            )
        ).fetchone()
        if not existing:
            conn.execute(
                feature_gates_table.insert().values(
                    id=str(_uuid.uuid4()),
                    feature_key=gate["feature_key"],
                    required_tier=gate["required_tier"],
                    description=gate["description"],
                )
            )


def downgrade() -> None:
    feature_gates_table = sa.table(
        "feature_gates",
        sa.column("feature_key", sa.String),
    )
    conn = op.get_bind()
    for gate in FAMILY_PLUS_GATES:
        conn.execute(
            feature_gates_table.delete().where(
                feature_gates_table.c.feature_key == gate["feature_key"]
            )
        )
