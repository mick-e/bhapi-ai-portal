"""Age tier rules engine — permission matrix per ADR-009.

Three tiers:
  YOUNG   (5-9)   — heavily restricted, pre-publish moderation
  PRETEEN (10-12) — moderate restrictions, pre-publish moderation
  TEEN    (13-15) — lighter restrictions, post-publish moderation
"""

from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any


class AgeTier(StrEnum):
    """Age tier categories per ADR-009."""

    YOUNG = "young"      # 5-9
    PRETEEN = "preteen"  # 10-12
    TEEN = "teen"        # 13-15


# ---------------------------------------------------------------------------
# Permission matrix — 18 permissions per tier
# ---------------------------------------------------------------------------

TIER_PERMISSIONS: dict[AgeTier, dict[str, Any]] = {
    AgeTier.YOUNG: {
        "can_post": True,
        "can_comment": True,
        "can_message": False,
        "can_like": True,
        "can_follow": True,
        "can_create_group_chat": False,
        "can_search_users": False,
        "can_upload_image": True,
        "can_upload_video": False,
        "can_use_ai_chat": False,
        "can_share_location": False,
        "can_add_contacts": False,
        "moderation_mode": "pre_publish",
        "max_contacts": 5,
        "max_post_length": 200,
        "max_daily_posts": 5,
        "max_message_length": 0,
        "content_filter_level": "strict",
    },
    AgeTier.PRETEEN: {
        "can_post": True,
        "can_comment": True,
        "can_message": True,
        "can_like": True,
        "can_follow": True,
        "can_create_group_chat": False,
        "can_search_users": True,
        "can_upload_image": True,
        "can_upload_video": False,
        "can_use_ai_chat": False,
        "can_share_location": False,
        "can_add_contacts": True,
        "moderation_mode": "pre_publish",
        "max_contacts": 20,
        "max_post_length": 500,
        "max_daily_posts": 15,
        "max_message_length": 300,
        "content_filter_level": "moderate",
    },
    AgeTier.TEEN: {
        "can_post": True,
        "can_comment": True,
        "can_message": True,
        "can_like": True,
        "can_follow": True,
        "can_create_group_chat": True,
        "can_search_users": True,
        "can_upload_image": True,
        "can_upload_video": True,
        "can_use_ai_chat": True,
        "can_share_location": False,
        "can_add_contacts": True,
        "moderation_mode": "post_publish",
        "max_contacts": 50,
        "max_post_length": 1000,
        "max_daily_posts": 30,
        "max_message_length": 1000,
        "content_filter_level": "standard",
    },
}


def age_from_dob(dob: date | datetime) -> int:
    """Calculate age in years from date of birth.

    Uses today's date in UTC. Handles leap-year birthdays correctly.
    """
    if isinstance(dob, datetime):
        dob = dob.date()
    today = datetime.now(timezone.utc).date()
    age = today.year - dob.year
    # Subtract 1 if birthday hasn't occurred yet this year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age


def get_tier_for_age(age: int) -> AgeTier | None:
    """Return the age tier for a given age, or None if outside range.

    Tiers: YOUNG (5-9), PRETEEN (10-12), TEEN (13-15).
    Returns None for ages < 5 or > 15.
    """
    if 5 <= age <= 9:
        return AgeTier.YOUNG
    if 10 <= age <= 12:
        return AgeTier.PRETEEN
    if 13 <= age <= 15:
        return AgeTier.TEEN
    return None


def get_permissions(
    tier: AgeTier,
    feature_overrides: dict[str, Any] | None = None,
    locked_features: list[str] | None = None,
) -> dict[str, Any]:
    """Get the effective permission set for a tier.

    Args:
        tier: The age tier.
        feature_overrides: Dict of permission overrides (parent/admin can
            grant or restrict specific permissions).
        locked_features: List of permission names that are forcibly disabled
            (cannot be overridden).
    """
    # Start with base permissions
    perms = dict(TIER_PERMISSIONS[tier])

    # Apply overrides (parents can customize)
    if feature_overrides:
        for key, value in feature_overrides.items():
            if key in perms:
                perms[key] = value

    # Apply locked features (admin/platform locks — override everything)
    if locked_features:
        for key in locked_features:
            if key in perms:
                # Boolean permissions become False, numeric become 0
                if isinstance(perms[key], bool):
                    perms[key] = False
                elif isinstance(perms[key], int):
                    perms[key] = 0
                elif isinstance(perms[key], str):
                    perms[key] = "disabled"

    return perms


def check_permission(
    tier: AgeTier,
    permission: str,
    feature_overrides: dict[str, Any] | None = None,
    locked_features: list[str] | None = None,
) -> bool:
    """Check whether a specific permission is allowed.

    For boolean permissions, returns the value directly.
    For numeric permissions, returns True if > 0.
    For string permissions, returns True if not "disabled".
    Returns False for unknown permissions.
    """
    perms = get_permissions(tier, feature_overrides, locked_features)
    value = perms.get(permission)
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value > 0
    if isinstance(value, str):
        return value != "disabled"
    return False
