"""Shared constants."""

# Auth
SESSION_COOKIE_NAME = "bhapi_session"
AUTH_HEADER = "Authorization"

# Supported AI platforms
AI_PLATFORMS = {
    "chatgpt": {
        "name": "ChatGPT",
        "provider": "OpenAI",
        "domains": ["chat.openai.com", "chatgpt.com"],
    },
    "gemini": {
        "name": "Gemini",
        "provider": "Google",
        "domains": ["gemini.google.com"],
    },
    "copilot": {
        "name": "Copilot",
        "provider": "Microsoft",
        "domains": ["copilot.microsoft.com"],
    },
    "claude": {
        "name": "Claude",
        "provider": "Anthropic",
        "domains": ["claude.ai"],
    },
    "grok": {
        "name": "Grok",
        "provider": "xAI",
        "domains": ["grok.com", "x.com/i/grok"],
    },
}

# Account types
ACCOUNT_TYPES = ("family", "school", "club")

# Group roles
ROLES = {
    "parent": {"display": "Parent/Guardian", "admin": True},
    "member": {"display": "Member", "admin": False},
    "school_admin": {"display": "School Administrator", "admin": True},
    "club_admin": {"display": "Club Administrator", "admin": True},
}

# Risk severity levels
SEVERITY_LEVELS = ("critical", "high", "medium", "low")

# Default limits
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100
MAX_GROUP_MEMBERS = 500
MAX_GROUPS_PER_USER = 20

# Stripe plans
STRIPE_PLANS = {
    "family_monthly": "Family Monthly",
    "family_annual": "Family Annual",
    "school_monthly": "School Monthly",
    "school_annual": "School Annual",
    "club_monthly": "Club Monthly",
    "club_annual": "Club Annual",
}

# Trial
FREE_TRIAL_DAYS = 14

# Alert re-notification intervals (seconds)
RENOTIFY_INTERVALS = {
    "critical": 900,   # 15 minutes
    "high": 1800,      # 30 minutes
    "medium": 3600,    # 1 hour
    "low": 86400,      # 24 hours
}

# Content retention
RISK_AUDIT_LOG_RETENTION_MONTHS = 12
CONTENT_EXCERPT_RETENTION_MONTHS = 12
