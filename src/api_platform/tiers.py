"""Public API GA rate-tier plan definitions.

Frozen dataclass tiers for the 4 public API pricing plans.
These are code-level constants (not DB-stored) used by the metering system.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class APITier:
    """Immutable API tier definition."""

    name: str
    monthly_request_quota: int
    requests_per_minute: int
    webhooks_enabled: bool
    sandbox_only: bool
    price_monthly: float


FREE_TIER = APITier("free", 10_000, 60, False, True, 0.0)
DEVELOPER_TIER = APITier("developer", 100_000, 300, True, False, 49.0)
BUSINESS_TIER = APITier("business", 1_000_000, 1500, True, False, 299.0)
ENTERPRISE_TIER = APITier("enterprise", 10_000_000, 6000, True, False, 1499.0)

TIERS = {t.name: t for t in [FREE_TIER, DEVELOPER_TIER, BUSINESS_TIER, ENTERPRISE_TIER]}


def get_tier(name: str) -> APITier:
    """Get a tier by name. Raises ValueError for unknown tiers."""
    if name not in TIERS:
        raise ValueError(f"Unknown API tier: {name}")
    return TIERS[name]
