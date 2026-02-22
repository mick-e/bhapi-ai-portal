"""Age verification and consent flow logic."""

from datetime import datetime, timezone


def calculate_age(date_of_birth: datetime) -> int:
    """Calculate age from date of birth."""
    today = datetime.now(timezone.utc)
    dob = date_of_birth if date_of_birth.tzinfo else date_of_birth.replace(tzinfo=timezone.utc)
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age


def requires_consent(date_of_birth: datetime | None, jurisdiction: str = "us") -> bool:
    """Check if a member requires parental/guardian consent.

    Consent thresholds by jurisdiction:
    - US (COPPA): under 13
    - EU/UK (GDPR): under 16
    - Brazil (LGPD): under 18
    - Australia: under 16
    """
    if date_of_birth is None:
        return False

    age = calculate_age(date_of_birth)

    thresholds = {
        "us": 13,
        "eu": 16,
        "uk": 16,
        "br": 18,
        "au": 16,
    }

    threshold = thresholds.get(jurisdiction, 16)
    return age < threshold


def get_consent_type(date_of_birth: datetime | None, jurisdiction: str = "us") -> str | None:
    """Get the applicable consent type for a member.

    Returns None if no consent required.
    """
    if date_of_birth is None:
        return None

    age = calculate_age(date_of_birth)

    if jurisdiction == "us" and age < 13:
        return "coppa"
    elif jurisdiction in ("eu", "uk") and age < 16:
        return "gdpr"
    elif jurisdiction == "br" and age < 18:
        return "lgpd"
    elif jurisdiction == "au" and age < 16:
        return "au_privacy"

    return None
