"""Plan tier definitions for Bhapi AI Safety Portal."""

PLAN_TIERS = {
    "free": {
        "name": "Free",
        "description": "Basic AI safety monitoring — free forever",
        "price_monthly": 0,
        "price_annual": 0,
        "member_limit": 1,
        "platform_limit": 3,
        "features": [
            "Monitor 1 child on up to 3 AI platforms",
            "Basic safety alerts (email only)",
            "Daily activity summary",
            "Community safety ratings",
        ],
        "stripe_price_monthly": None,
        "stripe_price_annual": None,
    },
    "family": {
        "name": "Family",
        "description": "AI safety monitoring for your family",
        "price_monthly": 9.99,
        "price_annual": 99.99,
        "member_limit": 5,
        "platform_limit": 10,
        "features": [
            "Monitor up to 5 family members",
            "Real-time AI usage alerts",
            "Risk classification & safety scores",
            "LLM spend tracking & budgets",
            "Weekly email digests",
            "Content blocking rules",
            "PDF & CSV reports",
        ],
        "stripe_price_monthly": "price_family_monthly",
        "stripe_price_annual": "price_family_annual",
    },
    "bundle": {
        "name": "App + Portal Bundle",
        "description": "Bhapi App + AI Portal — complete family safety",
        "price_monthly": 14.99,
        "price_annual": 149.99,
        "member_limit": 5,
        "platform_limit": 10,
        "features": [
            "Everything in Family Plan",
            "Bhapi App for mobile monitoring",
            "Cross-product alert correlation",
            "Unified family dashboard",
            "Priority support",
        ],
        "stripe_price_monthly": "price_bundle_monthly",
        "stripe_price_annual": "price_bundle_annual",
    },
    "school": {
        "name": "School Starter",
        "description": "AI governance for schools and educators",
        "price_monthly": 2.99,
        "price_annual": 29.99,
        "price_unit": "per student/month",
        "member_limit": 500,
        "platform_limit": 10,
        "features": [
            "Everything in Family, plus:",
            "Unlimited students (per-seat pricing)",
            "SIS integration (Clever, ClassLink, Canvas, PowerSchool)",
            "Class-level grouping & teacher alerts",
            "Safeguarding lead reports",
            "Federated SSO (Google Workspace, Microsoft Entra)",
            "Behaviour analytics & anomaly detection",
            "COPPA & FERPA compliance tools",
        ],
        "stripe_price_monthly": "price_school_monthly",
        "stripe_price_annual": "price_school_annual",
    },
    "enterprise": {
        "name": "Enterprise",
        "description": "Full-featured AI safety platform for large organisations",
        "price_monthly": None,
        "price_annual": None,
        "price_unit": "custom",
        "member_limit": None,
        "platform_limit": None,
        "features": [
            "Everything in School, plus:",
            "Unlimited groups & members",
            "Dedicated account manager",
            "Custom risk taxonomy configuration",
            "API access for third-party integration",
            "Vendor risk scoring",
            "Priority support & SLA",
            "Custom compliance reporting",
        ],
        "stripe_price_monthly": None,
        "stripe_price_annual": None,
    },
}


def get_plan(plan_type: str) -> dict | None:
    """Get a single plan tier by type."""
    return PLAN_TIERS.get(plan_type)


def get_all_plans() -> list[dict]:
    """Get all plan tiers with their type keys."""
    return [{"plan_type": k, **v} for k, v in PLAN_TIERS.items()]
