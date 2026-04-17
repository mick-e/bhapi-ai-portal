"""Bundle pricing tier definitions and helpers."""

TIERS = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "price_annual": 0,
        "max_children": 1,
        "max_parents": 1,
        "features": ["extension_monitoring", "weekly_email_summary"],
        "stripe_product_id": None,  # No Stripe for free
    },
    "family": {
        "name": "Family",
        "price_monthly": 9.99,
        "price_annual": 95.90,  # 20% discount
        "max_children": 5,
        "max_parents": 2,
        "features": [
            "extension_monitoring",
            "weekly_email_summary",
            "real_time_alerts",
            "blocking",
            "reports",
            "social_access",
            "unified_dashboard",
            "safety_app",
            "social_app",
        ],
        "stripe_product_id": "prod_family",
    },
    "family_plus": {
        "name": "Bhapi Family+",
        "price_monthly": 19.99,
        "price_annual": 199.99,
        "max_children": 8,
        "max_parents": 2,
        "features": [
            "*family",
            "location_tracking",
            "screen_time",
            "creative_tools",
            "intel_network_signals",
            "identity_protection_partner",
            "priority_support",
        ],
        "stripe_product_id": "prod_family_plus",
    },
    "school": {
        "name": "School",
        "price_monthly": 4.99,  # per seat
        "price_annual": 47.90,  # per seat, 20% discount
        "max_children": None,  # unlimited
        "max_parents": None,
        "features": [
            "*family",
            "api_access",
            "compliance_reporting",
            "sis_integration",
            "governance",
            "school_checkin",
        ],
        "stripe_product_id": "prod_school",
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": None,  # custom
        "price_annual": None,
        "max_children": None,
        "max_parents": None,
        "features": ["*school", "sso", "dedicated_support", "custom_compliance", "sla"],
        "stripe_product_id": "prod_enterprise",
    },
}

# Tier hierarchy for access-level comparisons
TIER_HIERARCHY = ["free", "family", "family_plus", "school", "enterprise"]


def get_tier_features(tier_key: str) -> list[str]:
    """Resolve all features for a tier, including inherited features."""
    tier = TIERS.get(tier_key, TIERS["free"])
    features = []
    for f in tier["features"]:
        if f.startswith("*"):
            parent = f[1:]
            features.extend(get_tier_features(parent))
        else:
            features.append(f)
    return list(set(features))


def get_tier(tier_key: str) -> dict:
    """Get a single tier definition. Returns free tier for unknown keys."""
    return TIERS.get(tier_key, TIERS["free"])


def get_all_tiers() -> list[dict]:
    """Return all tier definitions with their key included."""
    return [{"tier_key": k, **v} for k, v in TIERS.items()]


def get_tier_level(tier_key: str) -> int:
    """Return the numeric level of a tier in the hierarchy (0 = lowest)."""
    try:
        return TIER_HIERARCHY.index(tier_key)
    except ValueError:
        return 0


def tier_has_access(user_tier: str, required_tier: str) -> bool:
    """Return True if user_tier meets or exceeds required_tier."""
    return get_tier_level(user_tier) >= get_tier_level(required_tier)


def annual_discount_pct(tier_key: str) -> float:
    """Return the annual discount percentage for a tier (0.0 if no pricing)."""
    tier = TIERS.get(tier_key)
    if not tier:
        return 0.0
    monthly = tier.get("price_monthly")
    annual = tier.get("price_annual")
    if not monthly or not annual or monthly == 0:
        return 0.0
    # Annual is billed as lump sum; compare to 12 * monthly
    annual_if_monthly = monthly * 12
    return round((annual_if_monthly - annual) / annual_if_monthly * 100, 1)
