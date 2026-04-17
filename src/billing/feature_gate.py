"""Feature gating for free tier and plan-based access control.

Provides two complementary gating mechanisms:
- Static plan limits (PLAN_LIMITS) — fast, in-memory checks for legacy feature keys.
- DB-backed FeatureGate model — dynamic tier-hierarchy checks for Phase 3 features.
"""

from uuid import UUID

import structlog
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import get_current_user
from src.billing.models import FeatureGate, Subscription
from src.database import get_db
from src.exceptions import ForbiddenError

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Tier hierarchy (used by check_feature_gate dependency factory)
# ---------------------------------------------------------------------------

TIER_HIERARCHY = ["free", "family", "family_plus", "school", "enterprise"]

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
    "family_plus": {
        "member_limit": 8,
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
            "webhooks": True,
            "custom_taxonomy": False,
            "location_tracking": True,
            "screen_time_management": True,
            "creative_tools": True,
            "intel_network_signals": True,
            "identity_protection_partner": True,
            "priority_support": True,
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


# ---------------------------------------------------------------------------
# DB-backed feature gate dependency factory (Phase 3)
# ---------------------------------------------------------------------------


def check_feature_gate(feature_key: str):
    """FastAPI dependency factory. Returns a dependency that checks tier access.

    Usage::

        @router.get("/location")
        async def get_location(
            _gate: None = Depends(check_feature_gate("location_tracking")),
        ):
            ...
    """

    async def _check(
        auth=Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        gate_result = await db.execute(
            select(FeatureGate).where(FeatureGate.feature_key == feature_key)
        )
        gate = gate_result.scalar_one_or_none()
        if gate is None:
            return  # No gate = feature not gated = allowed

        # Get user's subscription tier (most recent active sub)
        group_id = getattr(auth, "group_id", None)
        sub_result = await db.execute(
            select(Subscription)
            .where(
                Subscription.group_id == group_id,
                Subscription.status.in_(["active", "trialing", "past_due"]),
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        sub = sub_result.scalar_one_or_none()
        user_tier = sub.plan_type if sub else "free"
        if user_tier == "starter":
            user_tier = "family"

        # Check tier hierarchy
        user_level = TIER_HIERARCHY.index(user_tier) if user_tier in TIER_HIERARCHY else 0
        required_level = (
            TIER_HIERARCHY.index(gate.required_tier)
            if gate.required_tier in TIER_HIERARCHY
            else 0
        )

        if user_level < required_level:
            raise ForbiddenError(
                f"This feature requires {gate.required_tier} tier or higher. "
                f"Upgrade at /pricing"
            )

    return _check


async def check_tier_access(db: AsyncSession, group_id: UUID, feature_key: str) -> None:
    """Programmatic tier check (non-dependency version).

    Raises ForbiddenError if the group's subscription tier does not meet
    the requirement recorded in feature_gates for feature_key.
    Uses the most recent active/trialing subscription; cancelled subs → free.
    """
    gate_result = await db.execute(
        select(FeatureGate).where(FeatureGate.feature_key == feature_key)
    )
    gate = gate_result.scalar_one_or_none()
    if gate is None:
        return  # ungated

    # Get the most recent active subscription for the group
    sub_result = await db.execute(
        select(Subscription)
        .where(
            Subscription.group_id == group_id,
            Subscription.status.in_(["active", "trialing", "past_due"]),
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = sub_result.scalar_one_or_none()
    user_tier = sub.plan_type if sub else "free"

    # Normalise legacy tier
    if user_tier == "starter":
        user_tier = "family"

    user_level = TIER_HIERARCHY.index(user_tier) if user_tier in TIER_HIERARCHY else 0
    required_level = (
        TIER_HIERARCHY.index(gate.required_tier)
        if gate.required_tier in TIER_HIERARCHY
        else 0
    )

    if user_level < required_level:
        raise ForbiddenError(
            f"This feature requires {gate.required_tier} tier or higher. "
            f"Upgrade at /pricing"
        )
