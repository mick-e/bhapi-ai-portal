"""VPN / proxy / incognito / tampering bypass detection.

Phase 4 Task 23 (R-24). Receives bypass-attempt events from the browser
extension or device agent, persists them, raises a high-severity alert to
group admins, and auto-blocks the member when 3+ attempts of any type are
recorded within a 60-minute rolling window.

Design notes
------------
- Detection happens client-side (extension + device agent). This module is
  the server-side recorder + escalation engine.
- ``bypass_type`` accepts: vpn, proxy, alt_url, incognito, tampering.
- Auto-block creates a ``BlockRule`` with reason="vpn_bypass_auto" tied to
  the same member, expiring 24h later (configurable per group later).
- Idempotent: repeated identical attempts within a 60s window are coalesced
  to avoid spam from a misbehaving extension.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert
from src.blocking.models import BlockRule, BypassAttempt
from src.exceptions import ValidationError
from src.groups.models import Group

logger = structlog.get_logger()


VALID_BYPASS_TYPES = frozenset({"vpn", "proxy", "alt_url", "incognito", "tampering"})

AUTO_BLOCK_THRESHOLD = 3
AUTO_BLOCK_WINDOW_MINUTES = 60
AUTO_BLOCK_DURATION_HOURS = 24
COALESCE_WINDOW_SECONDS = 60


async def record_bypass_attempt(
    db: AsyncSession,
    *,
    group_id: UUID,
    member_id: UUID,
    bypass_type: str,
    detection_signals: dict | None = None,
    user_agent: str | None = None,
) -> BypassAttempt:
    """Persist a bypass-attempt event. Coalesces repeated identical events
    within ``COALESCE_WINDOW_SECONDS`` and triggers ``maybe_auto_block`` at
    the threshold.
    """
    if bypass_type not in VALID_BYPASS_TYPES:
        raise ValidationError(
            f"Unknown bypass_type {bypass_type!r}. "
            f"Valid types: {', '.join(sorted(VALID_BYPASS_TYPES))}."
        )

    coalesce_cutoff = datetime.now(timezone.utc) - timedelta(seconds=COALESCE_WINDOW_SECONDS)
    recent = (
        await db.execute(
            select(BypassAttempt)
            .where(
                BypassAttempt.group_id == group_id,
                BypassAttempt.member_id == member_id,
                BypassAttempt.bypass_type == bypass_type,
                BypassAttempt.created_at >= coalesce_cutoff,
            )
            .order_by(BypassAttempt.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if recent is not None:
        logger.info(
            "bypass_attempt.coalesced",
            existing_id=str(recent.id),
            bypass_type=bypass_type,
            member_id=str(member_id),
        )
        return recent

    attempt = BypassAttempt(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        bypass_type=bypass_type,
        detection_signals=detection_signals or {},
        user_agent=user_agent,
        auto_blocked=False,
    )
    db.add(attempt)
    await db.flush()

    logger.warning(
        "bypass_attempt.recorded",
        attempt_id=str(attempt.id),
        bypass_type=bypass_type,
        member_id=str(member_id),
        group_id=str(group_id),
    )

    blocked = await maybe_auto_block(
        db, group_id=group_id, member_id=member_id, source_attempt=attempt
    )
    if blocked:
        attempt.auto_blocked = True
        await db.flush()

    await _raise_admin_alert(
        db,
        group_id=group_id,
        member_id=member_id,
        bypass_type=bypass_type,
        auto_blocked=blocked,
    )

    await db.refresh(attempt)
    return attempt


async def maybe_auto_block(
    db: AsyncSession,
    *,
    group_id: UUID,
    member_id: UUID,
    source_attempt: BypassAttempt,
) -> bool:
    """If the member has ``AUTO_BLOCK_THRESHOLD`` attempts in the rolling
    window, create a 24h block rule and return True. Otherwise return False.

    Returns ``False`` if an active vpn_bypass_auto block already exists
    (idempotent on repeated triggering).
    """
    window_start = datetime.now(timezone.utc) - timedelta(minutes=AUTO_BLOCK_WINDOW_MINUTES)
    count = (
        await db.execute(
            select(func.count(BypassAttempt.id)).where(
                BypassAttempt.member_id == member_id,
                BypassAttempt.created_at >= window_start,
            )
        )
    ).scalar_one()
    if count < AUTO_BLOCK_THRESHOLD:
        return False

    existing_block = (
        await db.execute(
            select(BlockRule).where(
                BlockRule.member_id == member_id,
                BlockRule.active.is_(True),
                BlockRule.reason == "vpn_bypass_auto",
            )
        )
    ).scalar_one_or_none()
    if existing_block is not None:
        return False

    owner_id = (
        await db.execute(select(Group.owner_id).where(Group.id == group_id))
    ).scalar_one()

    block = BlockRule(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        platforms=None,
        reason="vpn_bypass_auto",
        active=True,
        created_by=owner_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=AUTO_BLOCK_DURATION_HOURS),
    )
    db.add(block)
    await db.flush()
    logger.warning(
        "bypass_attempt.auto_blocked",
        member_id=str(member_id),
        group_id=str(group_id),
        rule_id=str(block.id),
        attempt_count=count,
    )
    return True


async def _raise_admin_alert(
    db: AsyncSession,
    *,
    group_id: UUID,
    member_id: UUID,
    bypass_type: str,
    auto_blocked: bool,
) -> None:
    """Insert a high-severity Alert row directly so the school-admin SLA
    queue picks it up. Doesn't go through alerts.service.create_alert
    because we want to stay synchronous within the blocking transaction
    (no correlation enrichment side effects in the bypass path).
    """
    body = (
        f"A {bypass_type} bypass attempt was detected. "
        + ("AI access has been auto-blocked for 24 hours." if auto_blocked else "")
    )
    alert = Alert(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        risk_event_id=None,
        source="ai",
        severity="high",
        title=f"AI monitoring bypass detected ({bypass_type})",
        body=body.strip(),
        channel="portal",
        status="pending",
    )
    db.add(alert)
    await db.flush()
