"""Add correlation_rules and enriched_alerts tables with 14 default rules.

Revision ID: 050
Revises: 044
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa
from migration_helpers import table_exists

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# 14 default correlation rules seeded on upgrade
# ---------------------------------------------------------------------------

DEFAULT_RULES = [
    {
        "name": "emotional_dependency",
        "description": "AI dependency + social withdrawal → emotional dependency risk",
        "action_severity": "high",
        "notification_type": "alert",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "ai_session", "metric": "session_count", "operator": "gt",
                 "threshold_multiplier": 3.0, "window_hours": 168},
                {"source": "social_activity", "metric": "post_frequency", "operator": "lt",
                 "threshold_multiplier": 0.5, "window_hours": 168},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
    {
        "name": "academic_risk",
        "description": "AI usage spike + attendance drop → academic risk",
        "action_severity": "medium",
        "notification_type": "alert",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "ai_session", "metric": "session_count", "operator": "gt",
                 "threshold_multiplier": 2.0, "window_hours": 168},
                {"source": "device", "metric": "attendance_score", "operator": "lt",
                 "threshold_multiplier": 0.7, "window_hours": 168},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
    {
        "name": "self_harm",
        "description": "Harmful AI content + self-harm social posts → self-harm risk",
        "action_severity": "critical",
        "notification_type": "push",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "ai_session", "metric": "harmful_content_score", "operator": "gt",
                 "threshold_multiplier": 0.6, "window_hours": 48},
                {"source": "social_activity", "metric": "self_harm_signal", "operator": "gt",
                 "threshold_multiplier": 0.5, "window_hours": 48},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
    {
        "name": "evasion",
        "description": "Monitored AI drop + high screen time → evasion of monitoring",
        "action_severity": "medium",
        "notification_type": "alert",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "ai_session", "metric": "monitored_session_ratio", "operator": "lt",
                 "threshold_multiplier": 0.3, "window_hours": 72},
                {"source": "device", "metric": "total_screen_time_hours", "operator": "gt",
                 "threshold_multiplier": 5.0, "window_hours": 24},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
    {
        "name": "grooming_risk",
        "description": "New AI platform + sudden social contacts → grooming risk",
        "action_severity": "high",
        "notification_type": "push",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "ai_session", "metric": "new_platform_access", "operator": "gt",
                 "threshold_multiplier": 0.0, "window_hours": 72},
                {"source": "social_activity", "metric": "new_contact_count", "operator": "gt",
                 "threshold_multiplier": 3.0, "window_hours": 72},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
    {
        "name": "privacy_violation",
        "description": "PII in AI + PII in social posts → privacy violation",
        "action_severity": "high",
        "notification_type": "alert",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "ai_session", "metric": "pii_exposure_count", "operator": "gt",
                 "threshold_multiplier": 0.0, "window_hours": 24},
                {"source": "social_activity", "metric": "pii_post_count", "operator": "gt",
                 "threshold_multiplier": 0.0, "window_hours": 24},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
    {
        "name": "academic_integrity",
        "description": "AI-generated content shared socially → academic integrity concern",
        "action_severity": "medium",
        "notification_type": "email",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "ai_session", "metric": "generated_content_count", "operator": "gt",
                 "threshold_multiplier": 2.0, "window_hours": 48},
                {"source": "social_activity", "metric": "shared_ai_content_count", "operator": "gt",
                 "threshold_multiplier": 1.0, "window_hours": 48},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
    {
        "name": "safety_concern",
        "description": "Location anomaly + social silence → safety concern",
        "action_severity": "high",
        "notification_type": "push",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "device", "metric": "location_anomaly_score", "operator": "gt",
                 "threshold_multiplier": 0.7, "window_hours": 12},
                {"source": "social_activity", "metric": "post_frequency", "operator": "lt",
                 "threshold_multiplier": 0.1, "window_hours": 24},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
    {
        "name": "deepfake_risk",
        "description": "Deepfake detection + social sharing → deepfake risk",
        "action_severity": "high",
        "notification_type": "push",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "ai_session", "metric": "deepfake_score", "operator": "gt",
                 "threshold_multiplier": 0.6, "window_hours": 48},
                {"source": "social_activity", "metric": "media_share_count", "operator": "gt",
                 "threshold_multiplier": 1.0, "window_hours": 48},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
    {
        "name": "financial_risk",
        "description": "Budget overrun + dependency signals → financial risk",
        "action_severity": "medium",
        "notification_type": "email",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "ai_session", "metric": "budget_overage_ratio", "operator": "gt",
                 "threshold_multiplier": 1.5, "window_hours": 168},
                {"source": "ai_session", "metric": "dependency_score", "operator": "gt",
                 "threshold_multiplier": 0.6, "window_hours": 168},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
    {
        "name": "sleep_disruption",
        "description": "Night-time AI usage + bedtime mode bypass → sleep disruption",
        "action_severity": "medium",
        "notification_type": "alert",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "ai_session", "metric": "night_session_count", "operator": "gt",
                 "threshold_multiplier": 2.0, "window_hours": 48},
                {"source": "device", "metric": "bedtime_bypass_count", "operator": "gt",
                 "threshold_multiplier": 0.0, "window_hours": 48},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
    {
        "name": "evasion_escalation",
        "description": "Multiple platform blocks bypassed → evasion escalation",
        "action_severity": "high",
        "notification_type": "push",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "device", "metric": "block_bypass_count", "operator": "gt",
                 "threshold_multiplier": 2.0, "window_hours": 72},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
    {
        "name": "dependency_escalation",
        "description": "Social isolation score increasing + AI chatbot reliance → dependency escalation",
        "action_severity": "high",
        "notification_type": "alert",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "social_activity", "metric": "isolation_score", "operator": "gt",
                 "threshold_multiplier": 0.65, "window_hours": 168},
                {"source": "ai_session", "metric": "chatbot_reliance_score", "operator": "gt",
                 "threshold_multiplier": 0.7, "window_hours": 168},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
    {
        "name": "stranger_danger",
        "description": "Sudden contact pattern change + location change → stranger danger",
        "action_severity": "critical",
        "notification_type": "sms",
        "age_tier_filter": None,
        "condition": {
            "signals": [
                {"source": "social_activity", "metric": "contact_change_rate", "operator": "gt",
                 "threshold_multiplier": 2.0, "window_hours": 24},
                {"source": "device", "metric": "location_change_count", "operator": "gt",
                 "threshold_multiplier": 1.0, "window_hours": 24},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
    },
]


def upgrade() -> None:
    import json
    from uuid import uuid4

    # Create correlation_rules table
    if not table_exists("correlation_rules"):
        op.create_table(
            "correlation_rules",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False, unique=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("condition", sa.JSON(), nullable=False),
            sa.Column("action_severity", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("notification_type", sa.String(30), nullable=False, server_default="alert"),
            sa.Column("age_tier_filter", sa.String(20), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_correlation_rules_enabled", "correlation_rules", ["enabled"])
        op.create_index("ix_correlation_rules_age_tier", "correlation_rules", ["age_tier_filter"])

    # Create enriched_alerts table
    if not table_exists("enriched_alerts"):
        op.create_table(
            "enriched_alerts",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("alert_id", sa.Uuid(), sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("correlation_rule_id", sa.Uuid(), sa.ForeignKey("correlation_rules.id", ondelete="SET NULL"), nullable=True),
            sa.Column("correlation_context", sa.Text(), nullable=False),
            sa.Column("contributing_signals", sa.JSON(), nullable=False),
            sa.Column("unified_risk_score", sa.Float(), nullable=False),
            sa.Column("confidence", sa.String(10), nullable=False, server_default="medium"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_enriched_alerts_alert_id", "enriched_alerts", ["alert_id"])
        op.create_index("ix_enriched_alerts_rule_id", "enriched_alerts", ["correlation_rule_id"])

    # Seed 14 default correlation rules
    conn = op.get_bind()
    # Only seed if table is empty
    existing = conn.execute(sa.text("SELECT COUNT(*) FROM correlation_rules")).scalar()
    if existing == 0:
        now = sa.func.now()
        for rule in DEFAULT_RULES:
            conn.execute(
                sa.text(
                    "INSERT INTO correlation_rules "
                    "(id, name, description, condition, action_severity, notification_type, age_tier_filter, enabled, created_at, updated_at) "
                    "VALUES (:id, :name, :description, :condition, :action_severity, :notification_type, :age_tier_filter, :enabled, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {
                    "id": str(uuid4()),
                    "name": rule["name"],
                    "description": rule["description"],
                    "condition": json.dumps(rule["condition"]),
                    "action_severity": rule["action_severity"],
                    "notification_type": rule["notification_type"],
                    "age_tier_filter": rule["age_tier_filter"],
                    "enabled": True,
                },
            )


def downgrade() -> None:
    op.drop_table("enriched_alerts")
    op.drop_table("correlation_rules")
