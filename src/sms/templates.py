"""Short SMS templates for notifications."""


def risk_alert_sms(member_name: str, severity: str, category: str) -> str:
    return f"[Bhapi {severity.upper()}] {category} detected for {member_name}. Check dashboard: bhapi.ai"


def spend_alert_sms(amount: float, budget: float, level: int) -> str:
    return f"[Bhapi] Budget alert: ${amount:.2f} of ${budget:.2f} spent ({level}%). Review: bhapi.ai/spend"


def digest_summary_sms(count: int, period: str) -> str:
    return f"[Bhapi] {count} alert{'s' if count != 1 else ''} in your {period} digest. Review: bhapi.ai"
