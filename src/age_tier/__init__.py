"""Age Tier permission engine — graduated feature unlocks for children."""

from src.age_tier.rules import (
    AgeTier,
    age_from_dob,
    check_permission,
    get_permissions,
    get_tier_for_age,
)

__all__ = [
    "AgeTier",
    "age_from_dob",
    "check_permission",
    "get_permissions",
    "get_tier_for_age",
]
