"""Feature gating for free tier and plan-based access control."""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models import Subscription
from src.exceptions import ForbiddenError

logger = structlog.get_logger()

# Feature limits per plan tier
PLAN_LIMITS = {
    "free": {
        "member_limit": 1,
        "platform_limit": 3,
        "features": {
            "basic_alerts": True,
            "pdf_reports": False,
            "csv_reports": False,
            "spend_tracking": False,
            "advanced_risk": False,
            "blocking_rules": False,
            "time_budgets": False,
            "sis_integration": False,
            "sso": False,
            "api_keys": False,
            "webhooks": False,
            "custom_taxonomy": False,
        },
    },
    "family": {
        "member_limit": 5,
        "platform_limit": 10,
        "features": {
            "basic_alerts": True,
            "pdf_reports": True,
            "csv_reports": True,
            "spend_tracking": True,
            "advanced_risk": True,
            "blocking_rules": True,
            "time_budgets": True,
            "sis_integration": False,
            "sso": False,
            "api_keys": True,
            "webhooks": False,
            "custom_taxonomy": False,
        },
    },
    "school": {
        "member_limit": 500,
        "platform_limit": 10,
        "features": {
            "basic_alerts": True,
            "pdf_reports": True,
            "csv_reports": True,
            "spend_tracking": True,
            "advanced_risk": True,
            "blocking_rules": True,
            "time_budgets": True,
            "sis_integration": True,
            "sso": True,
            "api_keys": True,
            "webhooks": True,
            "custom_taxonomy": False,
        },
    },
    "enterprise": {
        "member_limit": None,  # unlimited
        "platform_limit": None,  # unlimited
        "features": {
            "basic_alerts": True,
            "pdf_reports": True,
            "csv_reports": True,
            "spend_tracking": True,
            "advanced_risk": True,
            "blocking_rules": True,
            "time_budgets": True,
            "sis_integration": True,
            "sso": True,
            "api_keys": True,
            "webhooks": True,
            "custom_taxonomy": True,
        },
    },
}

# Alias: trialing users get family-level features
PLAN_LIMITS["trialing"] = PLAN_LIMITS["family"]
PLAN_LIMITS["starter"] = PLAN_LIMITS["family"]


def get_plan_limits(plan_type: str) -> dict:
    """Get feature limits for a plan tier."""
    return PLAN_LIMITS.get(plan_type, PLAN_LIMITS["free"])


def is_feature_enabled(plan_type: str, feature: str) -> bool:
    """Check if a specific feature is enabled for a plan."""
    limits = get_plan_limits(plan_type)
    return limits["features"].get(feature, False)


def get_member_limit(plan_type: str) -> int | None:
    """Get member limit for a plan. None means unlimited."""
    limits = get_plan_limits(plan_type)
    return limits["member_limit"]


def get_platform_limit(plan_type: str) -> int | None:
    """Get platform limit for a plan. None means unlimited."""
    limits = get_plan_limits(plan_type)
    return limits["platform_limit"]


async def get_group_plan(db: AsyncSession, group_id: UUID) -> str:
    """Get the current plan type for a group."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.group_id == group_id,
        ).order_by(Subscription.created_at.desc())
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        return "free"
    if subscription.status == "trialing":
        return "trialing"
    if subscription.status in ("active", "past_due"):
        return subscription.plan_type
    return "free"


async def require_feature(
    db: AsyncSession, group_id: UUID, feature: str
) -> None:
    """Raise ForbiddenError if the group's plan doesn't include a feature."""
    plan = await get_group_plan(db, group_id)
    if not is_feature_enabled(plan, feature):
        raise ForbiddenError(
            f"This feature requires an upgrade. Your current plan ({plan}) "
            f"does not include '{feature}'. Please upgrade to access this feature."
        )


async def get_feature_summary(db: AsyncSession, group_id: UUID) -> dict:
    """Get full feature access summary for a group."""
    plan = await get_group_plan(db, group_id)
    limits = get_plan_limits(plan)
    return {
        "plan": plan,
        "member_limit": limits["member_limit"],
        "platform_limit": limits["platform_limit"],
        "features": limits["features"],
    }
