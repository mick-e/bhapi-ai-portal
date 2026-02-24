"""Add compound indexes for dashboard performance.

Revision ID: 003
Revises: 002
Create Date: 2026-02-24

Adds compound indexes on the tables most queried by the BFF dashboard:
- alerts: (group_id, severity, created_at) for severity-filtered listings
- alerts: (group_id, status, created_at) for unread/pending alert queries
- capture_events: (group_id, member_id, timestamp) for per-member activity
- capture_events: (group_id, platform, timestamp) for platform filtering
- risk_events: (group_id, severity, created_at) for risk dashboard
- spend_records: (group_id, period_start, period_end) for spend summaries
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_alerts_group_severity_created",
        "alerts",
        ["group_id", "severity", "created_at"],
    )
    op.create_index(
        "ix_alerts_group_status_created",
        "alerts",
        ["group_id", "status", "created_at"],
    )
    op.create_index(
        "ix_capture_events_group_member_ts",
        "capture_events",
        ["group_id", "member_id", "timestamp"],
    )
    op.create_index(
        "ix_capture_events_group_platform_ts",
        "capture_events",
        ["group_id", "platform", "timestamp"],
    )
    op.create_index(
        "ix_risk_events_group_severity_created",
        "risk_events",
        ["group_id", "severity", "created_at"],
    )
    op.create_index(
        "ix_spend_records_group_period",
        "spend_records",
        ["group_id", "period_start", "period_end"],
    )


def downgrade() -> None:
    op.drop_index("ix_spend_records_group_period", table_name="spend_records")
    op.drop_index("ix_risk_events_group_severity_created", table_name="risk_events")
    op.drop_index("ix_capture_events_group_platform_ts", table_name="capture_events")
    op.drop_index("ix_capture_events_group_member_ts", table_name="capture_events")
    op.drop_index("ix_alerts_group_status_created", table_name="alerts")
    op.drop_index("ix_alerts_group_severity_created", table_name="alerts")
