"""Parent-friendly alert message templates.

"Calm Safety" principle: lead with what happened in plain language,
not technical severity labels. Parents respond better to
"Sam shared personal information" than "CRITICAL: PII_EXPOSURE".
"""

_CALM_MESSAGES: dict[str, str] = {
    "pii_exposure": "We noticed {member_name} shared personal information{platform_suffix}",
    "deepfake": "A suspicious image was found{platform_suffix} in {member_name}'s session",
    "safety_concern": "{member_name} may have encountered concerning content{platform_suffix}",
    "unusual_usage": "{member_name}'s AI usage changed significantly this week",
    "academic_integrity": "{member_name} may have used AI for schoolwork{platform_suffix}",
    "emotional_dependency": "{member_name} may be developing an emotional attachment to an AI{platform_suffix}",
    "grooming_risk": "We detected a potentially unsafe interaction involving {member_name}",
    "self_harm": "We noticed content that may indicate {member_name} is struggling",
    "privacy_violation": "{member_name}'s privacy settings may have been bypassed{platform_suffix}",
    "evasion": "{member_name} may be trying to avoid monitoring",
}

_SUGGESTED_ACTIONS: dict[str, str] = {
    "pii_exposure": "Talk to your child about sharing personal information online",
    "deepfake": "Review the content and discuss image safety with your child",
    "safety_concern": "Have a calm conversation about what they saw",
    "unusual_usage": "Check in about their AI usage habits this week",
    "academic_integrity": "Discuss responsible AI use for schoolwork",
    "emotional_dependency": "Encourage offline social activities and friendships",
    "grooming_risk": "Review the interaction details and consider contacting support",
    "self_harm": "Talk to your child with care and consider professional support",
    "privacy_violation": "Review your child's privacy settings together",
    "evasion": "Have an open conversation about monitoring and trust",
}

_DEFAULT_MESSAGE = "Something needs your attention regarding {member_name}"
_DEFAULT_ACTION = "Review the details and talk with your child"


def calm_message(alert_type: str, member_name: str, platform: str | None = None) -> str:
    """Generate a calm, parent-friendly alert message."""
    template = _CALM_MESSAGES.get(alert_type, _DEFAULT_MESSAGE)
    platform_suffix = f" in {platform}" if platform else ""
    return template.format(member_name=member_name, platform_suffix=platform_suffix)


def suggested_action(alert_type: str) -> str:
    """Get the suggested parent action for an alert type."""
    return _SUGGESTED_ACTIONS.get(alert_type, _DEFAULT_ACTION)
