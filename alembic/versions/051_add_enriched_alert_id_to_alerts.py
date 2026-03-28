"""Add enriched_alert_id FK column to alerts table.

Revision ID: 051
Revises: 050
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa
from migration_helpers import column_exists, index_exists

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not column_exists("alerts", "enriched_alert_id"):
        op.add_column(
            "alerts",
            sa.Column(
                "enriched_alert_id",
                sa.Uuid(),
                sa.ForeignKey("enriched_alerts.id"),
                nullable=True,
            ),
        )
    if not index_exists("alerts", "ix_alerts_enriched_alert_id"):
        op.create_index(
            "ix_alerts_enriched_alert_id",
            "alerts",
            ["enriched_alert_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_alerts_enriched_alert_id", table_name="alerts")
    op.drop_column("alerts", "enriched_alert_id")
