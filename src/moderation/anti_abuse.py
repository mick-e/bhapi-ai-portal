"""Anti-abuse detection — age misrepresentation, account farming, harassment.

Detection functions for:
  1. Age misrepresentation (vocabulary complexity, posting times)
  2. Account farming (device fingerprint clustering)
  3. Coordinated harassment (multiple reporters targeting same victim)
  4. Report abuse (reporter with low confirmation rate)
  5. Invitation rate limiting (daily limits per age tier)
  6. Content manipulation (Unicode homoglyphs, leetspeak normalization)
"""

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier.rules import AgeTier
from src.contacts.models import Contact
from src.device_agent.models import DeviceSession
from src.intelligence.models import AbuseSignal
from src.moderation.models import ContentReport

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Daily invitation limits per tier (P2-E7 spec)
INVITATION_LIMITS: dict[str, int] = {
    AgeTier.YOUNG: 3,
    AgeTier.PRETEEN: 10,
    AgeTier.TEEN: 10,
}

# Vocabulary complexity thresholds (average word length)
# Children 5-9 typically use ~4 char avg, 10-12 ~5 char avg
_YOUNG_MAX_AVG_WORD_LEN = 5.0
_PRETEEN_MAX_AVG_WORD_LEN = 6.5
_TEEN_MAX_AVG_WORD_LEN = 8.0

# Late-night posting hours (too late for young/preteen)
_YOUNG_CURFEW_START = 20   # 8 PM
_YOUNG_CURFEW_END = 7      # 7 AM
_PRETEEN_CURFEW_START = 22  # 10 PM
_PRETEEN_CURFEW_END = 6     # 6 AM

# Account farming — device fingerprint thresholds
_MAX_ACCOUNTS_PER_DEVICE = 3
_FARMING_WINDOW_DAYS = 30

# Coordinated harassment — threshold for reports against a single target
_HARASSMENT_REPORTER_THRESHOLD = 3
_HARASSMENT_WINDOW_HOURS = 24

# Report abuse — minimum reports and max dismiss rate
_MIN_REPORTS_FOR_ABUSE_CHECK = 5
_MAX_DISMISS_RATE = 0.8  # 80% dismissed = likely abusing reports

# Leetspeak / Unicode homoglyph mappings
_LEETSPEAK_MAP: dict[str, str] = {
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
    "7": "t", "8": "b", "9": "g", "@": "a", "$": "s",
    "!": "i", "|": "l", "+": "t", "(": "c", ")": "d",
}

# Unicode homoglyph normalization (Cyrillic/Greek lookalikes)
_HOMOGLYPH_MAP: dict[str, str] = {
    "\u0430": "a",  # Cyrillic а
    "\u0435": "e",  # Cyrillic е
    "\u043e": "o",  # Cyrillic о
    "\u0440": "p",  # Cyrillic р
    "\u0441": "c",  # Cyrillic с
    "\u0443": "y",  # Cyrillic у
    "\u0445": "x",  # Cyrillic х
    "\u0456": "i",  # Ukrainian і
    "\u0458": "j",  # Cyrillic ј
    "\u04bb": "h",  # Cyrillic һ
    "\u0391": "a",  # Greek Α (uppercase used as lowercase)
    "\u0392": "b",  # Greek Β
    "\u0395": "e",  # Greek Ε
    "\u0397": "h",  # Greek Η
    "\u0399": "i",  # Greek Ι
    "\u039a": "k",  # Greek Κ
    "\u039c": "m",  # Greek Μ
    "\u039d": "n",  # Greek Ν
    "\u039f": "o",  # Greek Ο
    "\u03a1": "p",  # Greek Ρ
    "\u03a4": "t",  # Greek Τ
    "\u03a5": "y",  # Greek Υ
    "\u03a7": "x",  # Greek Χ
    "\u03b1": "a",  # Greek α
    "\u03bf": "o",  # Greek ο
}


class AbuseType(StrEnum):
    """Types of detected abuse."""

    AGE_MISREPRESENTATION = "age_misrepresentation"
    ACCOUNT_FARMING = "account_farming"
    COORDINATED_HARASSMENT = "coordinated_harassment"
    REPORT_ABUSE = "report_abuse"
    INVITATION_RATE = "invitation_rate"
    CONTENT_MANIPULATION = "content_manipulation"


# ---------------------------------------------------------------------------
# 1. Age Misrepresentation Detection
# ---------------------------------------------------------------------------


def _compute_vocabulary_complexity(text: str) -> float:
    """Compute average word length as a proxy for vocabulary complexity."""
    words = re.findall(r"[a-zA-Z]+", text)
    if not words:
        return 0.0
    return sum(len(w) for w in words) / len(words)


def _is_curfew_violation(
    post_time: datetime,
    tier: str,
) -> bool:
    """Check whether a post was made during curfew hours for the given tier."""
    hour = post_time.hour
    if tier == AgeTier.YOUNG:
        return hour >= _YOUNG_CURFEW_START or hour < _YOUNG_CURFEW_END
    if tier == AgeTier.PRETEEN:
        return hour >= _PRETEEN_CURFEW_START or hour < _PRETEEN_CURFEW_END
    # Teens have no curfew restrictions
    return False


def detect_age_misrepresentation(
    text: str,
    post_times: list[datetime],
    claimed_tier: str,
) -> dict[str, Any]:
    """Detect signals that a user may be misrepresenting their age.

    Checks:
      - Vocabulary complexity vs expected for tier
      - Posting during curfew hours for tier

    Returns a dict with:
      - flagged: bool
      - signals: list of signal descriptions
      - severity: low/medium/high
      - vocabulary_complexity: float
      - curfew_violations: int
    """
    signals: list[str] = []
    vocab_complexity = _compute_vocabulary_complexity(text)

    # Check vocabulary complexity
    threshold = {
        AgeTier.YOUNG: _YOUNG_MAX_AVG_WORD_LEN,
        AgeTier.PRETEEN: _PRETEEN_MAX_AVG_WORD_LEN,
        AgeTier.TEEN: _TEEN_MAX_AVG_WORD_LEN,
    }.get(claimed_tier, _TEEN_MAX_AVG_WORD_LEN)

    if vocab_complexity > threshold:
        signals.append(
            f"Vocabulary complexity {vocab_complexity:.1f} exceeds "
            f"expected {threshold:.1f} for tier {claimed_tier}"
        )

    # Check curfew violations
    curfew_violations = sum(
        1 for t in post_times if _is_curfew_violation(t, claimed_tier)
    )
    if curfew_violations > 0:
        signals.append(
            f"{curfew_violations} posts during curfew hours for tier {claimed_tier}"
        )

    flagged = len(signals) > 0
    # Severity: both signals = high, one = medium
    if len(signals) >= 2:
        severity = "high"
    elif len(signals) == 1:
        severity = "medium"
    else:
        severity = "low"

    return {
        "flagged": flagged,
        "signals": signals,
        "severity": severity,
        "vocabulary_complexity": vocab_complexity,
        "curfew_violations": curfew_violations,
    }


# ---------------------------------------------------------------------------
# 2. Account Farming Detection
# ---------------------------------------------------------------------------


async def detect_account_farming(
    db: AsyncSession,
    device_id: str,
    window_days: int = _FARMING_WINDOW_DAYS,
) -> dict[str, Any]:
    """Detect multiple accounts registered from the same device fingerprint.

    Returns:
      - flagged: bool
      - account_count: int
      - member_ids: list of UUIDs sharing the device
      - severity: low/medium/high/critical
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    result = await db.execute(
        select(DeviceSession.member_id)
        .where(
            DeviceSession.device_id == device_id,
            DeviceSession.started_at >= cutoff,
        )
        .distinct()
    )
    member_ids = [row for row in result.scalars().all()]
    count = len(member_ids)

    flagged = count > _MAX_ACCOUNTS_PER_DEVICE
    if count > _MAX_ACCOUNTS_PER_DEVICE * 2:
        severity = "critical"
    elif count > _MAX_ACCOUNTS_PER_DEVICE:
        severity = "high"
    elif count > 1:
        severity = "medium"
    else:
        severity = "low"

    logger.info(
        "account_farming_check",
        device_id=device_id,
        account_count=count,
        flagged=flagged,
    )

    return {
        "flagged": flagged,
        "account_count": count,
        "member_ids": [str(m) for m in member_ids],
        "severity": severity,
    }


# ---------------------------------------------------------------------------
# 3. Coordinated Harassment Detection
# ---------------------------------------------------------------------------


async def detect_coordinated_harassment(
    db: AsyncSession,
    target_id: UUID,
    window_hours: int = _HARASSMENT_WINDOW_HOURS,
) -> dict[str, Any]:
    """Detect coordinated harassment — multiple reporters targeting same victim.

    Checks ContentReport for a spike in reports against a single target
    within a rolling window.

    Returns:
      - flagged: bool
      - reporter_count: int (unique reporters)
      - report_count: int (total reports)
      - severity: low/medium/high/critical
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    # Count total reports
    total_q = await db.execute(
        select(func.count(ContentReport.id)).where(
            ContentReport.target_id == target_id,
            ContentReport.created_at >= cutoff,
        )
    )
    report_count = total_q.scalar() or 0

    # Count unique reporters
    unique_q = await db.execute(
        select(func.count(func.distinct(ContentReport.reporter_id))).where(
            ContentReport.target_id == target_id,
            ContentReport.created_at >= cutoff,
        )
    )
    reporter_count = unique_q.scalar() or 0

    flagged = reporter_count >= _HARASSMENT_REPORTER_THRESHOLD
    if reporter_count >= _HARASSMENT_REPORTER_THRESHOLD * 3:
        severity = "critical"
    elif reporter_count >= _HARASSMENT_REPORTER_THRESHOLD * 2:
        severity = "high"
    elif flagged:
        severity = "medium"
    else:
        severity = "low"

    logger.info(
        "coordinated_harassment_check",
        target_id=str(target_id),
        reporter_count=reporter_count,
        report_count=report_count,
        flagged=flagged,
    )

    return {
        "flagged": flagged,
        "reporter_count": reporter_count,
        "report_count": report_count,
        "severity": severity,
    }


# ---------------------------------------------------------------------------
# 4. Report Abuse Detection
# ---------------------------------------------------------------------------


async def detect_report_abuse(
    db: AsyncSession,
    reporter_id: UUID,
) -> dict[str, Any]:
    """Detect users who abuse the reporting system (low confirmation rate).

    A reporter with many reports but very few confirmed (action_taken)
    may be weaponizing the report system.

    Returns:
      - flagged: bool
      - total_reports: int
      - dismissed_count: int
      - dismiss_rate: float (0-1)
      - severity: low/medium/high
    """
    # Total reports by this user
    total_q = await db.execute(
        select(func.count(ContentReport.id)).where(
            ContentReport.reporter_id == reporter_id,
        )
    )
    total_reports = total_q.scalar() or 0

    if total_reports < _MIN_REPORTS_FOR_ABUSE_CHECK:
        return {
            "flagged": False,
            "total_reports": total_reports,
            "dismissed_count": 0,
            "dismiss_rate": 0.0,
            "severity": "low",
        }

    # Dismissed reports
    dismissed_q = await db.execute(
        select(func.count(ContentReport.id)).where(
            ContentReport.reporter_id == reporter_id,
            ContentReport.status == "dismissed",
        )
    )
    dismissed_count = dismissed_q.scalar() or 0
    dismiss_rate = dismissed_count / total_reports if total_reports > 0 else 0.0

    flagged = dismiss_rate >= _MAX_DISMISS_RATE
    if dismiss_rate >= 0.95:
        severity = "high"
    elif flagged:
        severity = "medium"
    else:
        severity = "low"

    logger.info(
        "report_abuse_check",
        reporter_id=str(reporter_id),
        total_reports=total_reports,
        dismissed_count=dismissed_count,
        dismiss_rate=dismiss_rate,
        flagged=flagged,
    )

    return {
        "flagged": flagged,
        "total_reports": total_reports,
        "dismissed_count": dismissed_count,
        "dismiss_rate": dismiss_rate,
        "severity": severity,
    }


# ---------------------------------------------------------------------------
# 5. Invitation Rate Limiting
# ---------------------------------------------------------------------------


async def check_invitation_rate(
    db: AsyncSession,
    requester_id: UUID,
    tier: str,
) -> dict[str, Any]:
    """Check whether a user has exceeded their daily invitation limit.

    Limits per tier:
      - young (5-9): 3/day
      - preteen (10-12): 10/day
      - teen (13-15): 10/day

    Returns:
      - allowed: bool
      - sent_today: int
      - daily_limit: int
      - remaining: int
    """
    daily_limit = INVITATION_LIMITS.get(tier, 3)
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)

    result = await db.execute(
        select(func.count(Contact.id)).where(
            Contact.requester_id == requester_id,
            Contact.created_at >= cutoff,
        )
    )
    sent_today = result.scalar() or 0

    allowed = sent_today < daily_limit
    remaining = max(0, daily_limit - sent_today)

    logger.info(
        "invitation_rate_check",
        requester_id=str(requester_id),
        tier=tier,
        sent_today=sent_today,
        daily_limit=daily_limit,
        allowed=allowed,
    )

    return {
        "allowed": allowed,
        "sent_today": sent_today,
        "daily_limit": daily_limit,
        "remaining": remaining,
    }


# ---------------------------------------------------------------------------
# 6. Content Manipulation Detection (Unicode/Leetspeak)
# ---------------------------------------------------------------------------


def normalize_leetspeak(text: str) -> str:
    """Normalize leetspeak substitutions back to standard characters."""
    return "".join(_LEETSPEAK_MAP.get(ch, ch) for ch in text)


def normalize_homoglyphs(text: str) -> str:
    """Normalize Unicode homoglyphs (Cyrillic/Greek) to Latin equivalents."""
    result = []
    for ch in text:
        if ch in _HOMOGLYPH_MAP:
            result.append(_HOMOGLYPH_MAP[ch])
        else:
            # NFKD decomposition normalizes accented/combined forms
            decomposed = unicodedata.normalize("NFKD", ch)
            # Take only the base character (strip combining marks)
            base = "".join(
                c for c in decomposed if not unicodedata.combining(c)
            )
            result.append(base if base else ch)
    return "".join(result)


def check_content_manipulation(
    text: str,
    blocklist: list[str] | None = None,
) -> dict[str, Any]:
    """Detect content manipulation via Unicode homoglyphs or leetspeak.

    Normalizes text and checks against an optional blocklist.

    Returns:
      - manipulated: bool
      - normalized_text: str
      - homoglyph_count: int
      - leetspeak_count: int
      - matched_terms: list of blocked terms found after normalization
    """
    # Count manipulation characters
    homoglyph_count = sum(1 for ch in text if ch in _HOMOGLYPH_MAP)
    leetspeak_count = sum(1 for ch in text if ch in _LEETSPEAK_MAP)

    # Normalize
    normalized = normalize_homoglyphs(text)
    normalized = normalize_leetspeak(normalized)
    normalized_lower = normalized.lower()

    # Check blocklist
    matched_terms: list[str] = []
    if blocklist:
        for term in blocklist:
            if term.lower() in normalized_lower:
                matched_terms.append(term)

    manipulated = (homoglyph_count > 0 or leetspeak_count > 0) and len(matched_terms) > 0

    return {
        "manipulated": manipulated,
        "normalized_text": normalized,
        "homoglyph_count": homoglyph_count,
        "leetspeak_count": leetspeak_count,
        "matched_terms": matched_terms,
    }


# ---------------------------------------------------------------------------
# Persistence helper — record abuse signal in DB
# ---------------------------------------------------------------------------


async def record_abuse_signal(
    db: AsyncSession,
    member_id: UUID,
    signal_type: str,
    severity: str,
    details: dict[str, Any] | None = None,
) -> AbuseSignal:
    """Persist an abuse signal in the intelligence module's AbuseSignal table."""
    signal = AbuseSignal(
        id=uuid4(),
        member_id=member_id,
        signal_type=signal_type,
        severity=severity,
        details=details,
    )
    db.add(signal)
    await db.flush()
    await db.refresh(signal)

    logger.warning(
        "abuse_signal_recorded",
        member_id=str(member_id),
        signal_type=signal_type,
        severity=severity,
    )
    return signal
