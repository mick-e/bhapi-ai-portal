"""Intelligence Network business logic."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError
from src.intelligence_network.anonymizer import anonymize_signal
from src.intelligence_network.models import (
    AnonymizationAudit,
    NetworkSubscription,
    SignalDelivery,
    ThreatSignal,
)

logger = structlog.get_logger()

# Severity ordering for filtering
_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


async def contribute_signal(
    db: AsyncSession,
    group_id: uuid.UUID,
    raw_event: dict,
) -> ThreatSignal:
    """Anonymize a raw event and store it as a shared threat signal.

    Args:
        db: Database session.
        group_id: The contributing group (stored only in anonymization audit).
        raw_event: Raw event dict which may contain PII.

    Returns:
        The created ThreatSignal (anonymized).
    """
    anonymized = anonymize_signal(raw_event)
    stripped_fields = anonymized.pop("_stripped_fields", [])

    signal = ThreatSignal(
        id=uuid.uuid4(),
        signal_type=raw_event.get("signal_type", "unknown"),
        severity=raw_event.get("severity", "medium"),
        pattern_data=anonymized.get("pattern_data", anonymized),
        sample_size=1,
        contributor_region=anonymized.get("contributor_region"),
        confidence=raw_event.get("confidence", 0.5),
        description=anonymized.get("description"),
    )
    db.add(signal)
    await db.flush()

    # Record anonymization audit
    audit = AnonymizationAudit(
        id=uuid.uuid4(),
        signal_id=signal.id,
        source_group_id=group_id,
        fields_stripped=stripped_fields,
        k_anonymity_applied=False,
        dp_noise_applied=False,
    )
    db.add(audit)
    await db.flush()

    logger.info(
        "intel_network_signal_contributed",
        signal_id=str(signal.id),
        signal_type=signal.signal_type,
        severity=signal.severity,
        fields_stripped=len(stripped_fields),
    )

    return signal


async def subscribe(
    db: AsyncSession,
    group_id: uuid.UUID,
    signal_types: list[str] | None = None,
    min_severity: str = "medium",
) -> NetworkSubscription:
    """Subscribe a group to receive intelligence network signals.

    If the group already has a subscription, reactivate and update it.
    """
    result = await db.execute(
        select(NetworkSubscription).where(NetworkSubscription.group_id == group_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.is_active = True
        existing.signal_types = signal_types or []
        existing.minimum_severity = min_severity
        existing.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(existing)
        logger.info("intel_network_resubscribed", group_id=str(group_id))
        return existing

    sub = NetworkSubscription(
        id=uuid.uuid4(),
        group_id=group_id,
        is_active=True,
        signal_types=signal_types or [],
        minimum_severity=min_severity,
    )
    db.add(sub)
    await db.flush()
    logger.info("intel_network_subscribed", group_id=str(group_id))
    return sub


async def unsubscribe(db: AsyncSession, group_id: uuid.UUID) -> None:
    """Disable the group's intelligence network subscription."""
    result = await db.execute(
        select(NetworkSubscription).where(
            NetworkSubscription.group_id == group_id,
            NetworkSubscription.is_active.is_(True),
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise NotFoundError("No active subscription found")

    sub.is_active = False
    sub.updated_at = datetime.now(timezone.utc)
    await db.flush()
    logger.info("intel_network_unsubscribed", group_id=str(group_id))


async def fetch_signals_for_subscriber(
    db: AsyncSession,
    group_id: uuid.UUID,
    limit: int = 50,
) -> list[ThreatSignal]:
    """Fetch threat signals filtered by the group's subscription preferences.

    Only returns signals meeting the k-anonymity threshold (sample_size >= 5).
    Records each delivery in the audit log.
    """
    # Get subscription
    result = await db.execute(
        select(NetworkSubscription).where(
            NetworkSubscription.group_id == group_id,
            NetworkSubscription.is_active.is_(True),
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise NotFoundError("No active subscription found. Please subscribe first.")

    # Build query
    query = select(ThreatSignal).where(ThreatSignal.sample_size >= 5)

    # Filter by signal types if specified
    if sub.signal_types:
        query = query.where(ThreatSignal.signal_type.in_(sub.signal_types))

    # Filter by minimum severity
    min_sev_order = _SEVERITY_ORDER.get(sub.minimum_severity, 1)
    allowed_severities = [s for s, o in _SEVERITY_ORDER.items() if o >= min_sev_order]
    query = query.where(ThreatSignal.severity.in_(allowed_severities))

    query = query.order_by(ThreatSignal.created_at.desc()).limit(limit)

    result = await db.execute(query)
    signals = list(result.scalars().all())

    # Record deliveries
    for signal in signals:
        delivery = SignalDelivery(
            id=uuid.uuid4(),
            signal_id=signal.id,
            group_id=group_id,
        )
        db.add(delivery)

    if signals:
        await db.flush()

    logger.info(
        "intel_network_signals_delivered",
        group_id=str(group_id),
        count=len(signals),
    )

    return signals


async def submit_feedback(
    db: AsyncSession,
    signal_id: uuid.UUID,
    group_id: uuid.UUID,
    is_helpful: bool,
    notes: str | None = None,
) -> None:
    """Submit feedback on a threat signal."""
    result = await db.execute(
        select(ThreatSignal).where(ThreatSignal.id == signal_id)
    )
    signal = result.scalar_one_or_none()
    if not signal:
        raise NotFoundError("Signal not found")

    if is_helpful:
        signal.feedback_helpful += 1
    else:
        signal.feedback_false_positive += 1

    await db.flush()

    logger.info(
        "intel_network_feedback",
        signal_id=str(signal_id),
        group_id=str(group_id),
        is_helpful=is_helpful,
    )
