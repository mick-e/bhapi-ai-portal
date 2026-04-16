"""Alerts service — business logic for notifications and preferences."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert, NotificationPreference
from src.alerts.schemas import AlertCreate, PreferenceConfig
from src.exceptions import NotFoundError

logger = structlog.get_logger()


async def create_alert(db: AsyncSession, data: AlertCreate) -> Alert:
    """Create a new alert notification."""
    alert = Alert(
        id=uuid4(),
        group_id=data.group_id,
        member_id=data.member_id,
        risk_event_id=data.risk_event_id,
        source=data.source if hasattr(data, "source") else "ai",
        severity=data.severity,
        title=data.title,
        body=data.body,
        channel=data.channel,
        status="pending",
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)

    logger.info(
        "alert_created",
        alert_id=str(alert.id),
        severity=data.severity,
        channel=data.channel,
    )

    # Link enriched alert if correlation context exists for this alert's member + source
    try:
        from src.intelligence import create_enriched_alert, get_enriched_alert

        existing_enrichment = await get_enriched_alert(db, alert.id)
        if existing_enrichment is None and data.member_id is not None:
            # Build a lightweight event context for correlation evaluation
            event_context = {
                "source": data.source if hasattr(data, "source") else "ai",
                "member_id": str(data.member_id),
                "severity": data.severity,
                "metrics": {
                    "risk_score": 1.0 if data.severity in ("critical", "high") else 0.5,
                },
            }
            from src.intelligence.correlation import evaluate_event

            matches = await evaluate_event(db, event_context)
            if matches:
                best = matches[0]
                rule = best["rule"]
                signals = best["signals"]
                score = best["score"]
                confidence = best["confidence"]

                context_str = (
                    f"Correlated alert for member {data.member_id}: "
                    f"rule '{rule.name}' matched {len(signals)} signal(s) "
                    f"with score {score:.2f} [{confidence} confidence]"
                )
                enriched = await create_enriched_alert(
                    db,
                    alert_id=alert.id,
                    rule_id=rule.id,
                    context=context_str,
                    signals={"matched": signals, "source": event_context["source"]},
                    score=score,
                    confidence=confidence,
                )
                alert.enriched_alert_id = enriched.id
                await db.flush()
                await db.refresh(alert)
                logger.info(
                    "alert_enriched",
                    alert_id=str(alert.id),
                    enriched_id=str(enriched.id),
                    rule=rule.name,
                    confidence=confidence,
                )
    except Exception as exc:
        logger.warning(
            "alert_enrichment_failed",
            alert_id=str(alert.id),
            error=str(exc),
        )

    # Broadcast to SSE for real-time notification
    try:
        from src.alerts.sse import sse_manager

        await sse_manager.broadcast(alert.group_id, "new_alert", {
            "id": str(alert.id),
            "group_id": str(alert.group_id),
            "severity": alert.severity,
            "title": alert.title if hasattr(alert, "title") else "",
            "created_at": str(alert.created_at) if hasattr(alert, "created_at") else "",
        })
    except Exception as exc:
        # SSE failure must never block alert creation
        logger.debug(
            "alert_sse_notify_degraded",
            error=str(exc),
            alert_id=str(alert.id),
            group_id=str(alert.group_id),
        )

    # Best-effort push notification (never blocks alert creation)
    try:
        from src.alerts.push import expo_push_service
        from src.groups.models import Group

        group_result = await db.execute(select(Group).where(Group.id == data.group_id))
        group_obj = group_result.scalar_one_or_none()
        if group_obj and group_obj.owner_id:
            await expo_push_service.send_notification(
                db,
                user_id=group_obj.owner_id,
                title=f"Bhapi Alert: {data.title}",
                body=data.body[:200],
                data={"alert_id": str(alert.id), "severity": data.severity},
            )
    except Exception:
        logger.warning("push_delivery_failed", alert_id=str(alert.id))

    # Notify emergency contacts on critical alerts
    if data.severity == "critical":
        try:
            from src.groups.emergency_contacts import notify_emergency_contacts

            await notify_emergency_contacts(db, alert.group_id, {
                "severity": alert.severity,
                "title": alert.title,
                "body": alert.body,
            })
        except Exception as exc:
            # Emergency contact failure must never block alert creation
            logger.debug(
                "alert_emergency_contact_degraded",
                error=str(exc),
                alert_id=str(alert.id),
                group_id=str(alert.group_id),
            )

    return alert


async def list_alerts(
    db: AsyncSession,
    group_id: UUID,
    severity: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Alert]:
    """List alerts for a group with optional filters."""
    query = select(Alert).where(Alert.group_id == group_id)

    if severity:
        query = query.where(Alert.severity == severity)
    if status:
        query = query.where(Alert.status == status)

    query = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_alert(db: AsyncSession, alert_id: UUID) -> Alert:
    """Get a single alert by ID."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise NotFoundError("Alert", str(alert_id))
    return alert


async def acknowledge_alert(
    db: AsyncSession, alert_id: UUID, user_id: UUID
) -> Alert:
    """Acknowledge an alert."""
    alert = await get_alert(db, alert_id)
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = user_id
    await db.flush()
    await db.refresh(alert)

    logger.info("alert_acknowledged", alert_id=str(alert_id), user_id=str(user_id))
    return alert


async def get_preferences(
    db: AsyncSession, group_id: UUID, user_id: UUID
) -> list[NotificationPreference]:
    """Get notification preferences for a user in a group."""
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.group_id == group_id,
            NotificationPreference.user_id == user_id,
        )
    )
    return list(result.scalars().all())


_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


async def get_unified_alerts(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID | None = None,
    source_filter: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Get unified alerts across AI, social, and device sources.

    Returns paginated alerts sorted by severity (critical first) then timestamp (newest first).
    Optional filters: member_id, source (ai|social|device).
    """
    from sqlalchemy import case, func

    base = select(Alert).where(Alert.group_id == group_id)
    count_q = select(func.count(Alert.id)).where(Alert.group_id == group_id)

    if member_id:
        base = base.where(Alert.member_id == member_id)
        count_q = count_q.where(Alert.member_id == member_id)

    if source_filter:
        base = base.where(Alert.source == source_filter)
        count_q = count_q.where(Alert.source == source_filter)

    total = (await db.execute(count_q)).scalar() or 0

    # Sort by severity (critical first) then by created_at descending
    severity_sort = case(
        {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4},
        value=Alert.severity,
        else_=5,
    )
    offset = (page - 1) * page_size
    query = base.order_by(severity_sort, Alert.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    alerts = list(result.scalars().all())

    total_pages = max((total + page_size - 1) // page_size, 1)

    return {
        "items": alerts,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


async def create_social_alert(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    severity: str,
    title: str,
    body: str,
) -> Alert:
    """Create a social-source alert (e.g., when moderation rejects content)."""
    data = AlertCreate(
        group_id=group_id,
        member_id=member_id,
        source="social",
        severity=severity,
        title=title,
        body=body,
        channel="portal",
    )
    return await create_alert(db, data)


async def create_device_alert(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    severity: str,
    title: str,
    body: str,
) -> Alert:
    """Create a device-source alert (e.g., screen time exceeded, new app detected)."""
    data = AlertCreate(
        group_id=group_id,
        member_id=member_id,
        source="device",
        severity=severity,
        title=title,
        body=body,
        channel="portal",
    )
    return await create_alert(db, data)


async def update_preferences(
    db: AsyncSession,
    group_id: UUID,
    user_id: UUID,
    preferences: list[PreferenceConfig],
) -> list[NotificationPreference]:
    """Update notification preferences for a user in a group.

    Upserts preferences by category — creates new ones or updates existing.
    """
    existing = await get_preferences(db, group_id, user_id)
    existing_by_category = {p.category: p for p in existing}

    updated: list[NotificationPreference] = []

    for pref_config in preferences:
        if pref_config.category in existing_by_category:
            # Update existing preference
            pref = existing_by_category[pref_config.category]
            pref.channel = pref_config.channel
            pref.digest_mode = pref_config.digest_mode
            pref.enabled = pref_config.enabled
            updated.append(pref)
        else:
            # Create new preference
            pref = NotificationPreference(
                id=uuid4(),
                group_id=group_id,
                user_id=user_id,
                category=pref_config.category,
                channel=pref_config.channel,
                digest_mode=pref_config.digest_mode,
                enabled=pref_config.enabled,
            )
            db.add(pref)
            updated.append(pref)

    await db.flush()
    for p in updated:
        await db.refresh(p)

    logger.info(
        "preferences_updated",
        group_id=str(group_id),
        user_id=str(user_id),
        count=len(updated),
    )
    return updated
