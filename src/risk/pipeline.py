"""Risk pipeline orchestration — processes capture events through the full risk stack.

Entry point: process_capture_event()
Flow: CaptureEvent → engine.process_event() → risk_service.create_risk_event() → alerts_service.create_alert()
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert
from src.encryption import encrypt_credential
from src.alerts.schemas import AlertCreate
from src.alerts.service import create_alert
from src.capture.models import CaptureEvent
from src.groups.models import GroupMember
from src.risk.engine import process_event as run_pipeline
from src.risk.models import RiskConfig, RiskEvent
from src.risk.schemas import RiskClassification
from src.risk.service import create_risk_event
from src.risk.taxonomy import RISK_CATEGORIES

logger = structlog.get_logger()


async def process_capture_event(
    db: AsyncSession,
    capture_event: CaptureEvent,
) -> list[RiskEvent]:
    """Run a capture event through the full risk pipeline.

    1. Load group risk config + member age
    2. Run pipeline (PII → safety → rules)
    3. Create risk events for each classification
    4. Create alerts for each risk event
    5. Mark capture event as risk_processed=True

    Returns the list of created RiskEvent objects.
    """
    if capture_event.risk_processed:
        logger.debug("pipeline_skip_already_processed", event_id=str(capture_event.id))
        return []

    content = capture_event.content or ""
    if not content.strip():
        # No content to classify — mark as processed and return
        capture_event.risk_processed = True
        await db.flush()
        logger.debug("pipeline_skip_empty_content", event_id=str(capture_event.id))
        return []

    # Load group risk config
    config = await _load_risk_config(db, capture_event.group_id)

    # Load member age
    member_age = await _get_member_age(db, capture_event.member_id)

    # Build pipeline input
    capture_data = {
        "content": content,
        "platform": capture_event.platform,
        "event_type": capture_event.event_type,
        "session_id": capture_event.session_id,
    }

    # Run the multi-layer pipeline
    classifications = await run_pipeline(
        capture_event_data=capture_data,
        member_age=member_age,
        config=config,
        group_id=capture_event.group_id,
        member_id=capture_event.member_id,
        db=db,
    )

    # Create risk events and alerts
    risk_events: list[RiskEvent] = []
    for classification in classifications:
        risk_event = await create_risk_event(
            db=db,
            group_id=capture_event.group_id,
            member_id=capture_event.member_id,
            classification=classification,
            capture_event_id=capture_event.id,
            details={"source": "pipeline", "platform": capture_event.platform},
        )
        risk_events.append(risk_event)

        # Create encrypted content excerpt for this risk event
        if content.strip():
            from src.risk.models import ContentExcerpt
            excerpt = ContentExcerpt(
                id=uuid4(),
                risk_event_id=risk_event.id,
                encrypted_content=encrypt_credential(content[:2000]),
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            )
            db.add(excerpt)

        # Create alert for this risk event
        alert = await _create_alert_for_risk(db, capture_event, risk_event, classification)

        # Attempt immediate email delivery for critical/high alerts
        if alert:
            try:
                from src.alerts.delivery import deliver_risk_alert
                await deliver_risk_alert(db, alert)
            except Exception as exc:
                logger.warning("email_delivery_error", alert_id=str(alert.id), error=str(exc))

    # Mark capture event as processed
    capture_event.risk_processed = True
    await db.flush()

    logger.info(
        "pipeline_processed",
        event_id=str(capture_event.id),
        risk_count=len(risk_events),
        categories=[e.category for e in risk_events],
    )

    return risk_events


async def _load_risk_config(db: AsyncSession, group_id: UUID) -> dict[str, dict]:
    """Load per-category risk config for a group as a dict."""
    result = await db.execute(
        select(RiskConfig).where(RiskConfig.group_id == group_id)
    )
    configs = result.scalars().all()

    config_dict: dict[str, dict] = {}
    for cfg in configs:
        config_dict[cfg.category] = {
            "sensitivity": cfg.sensitivity,
            "enabled": cfg.enabled,
            "custom_keywords": cfg.custom_keywords or {},
        }
    return config_dict


async def _get_member_age(db: AsyncSession, member_id: UUID) -> int | None:
    """Get the member's age in years from date_of_birth."""
    result = await db.execute(
        select(GroupMember.date_of_birth).where(GroupMember.id == member_id)
    )
    dob = result.scalar_one_or_none()
    if not dob:
        return None

    now = datetime.now(timezone.utc)
    # Handle both timezone-aware and naive datetimes
    if dob.tzinfo is None:
        from datetime import timezone as tz
        dob = dob.replace(tzinfo=tz.utc)

    age = now.year - dob.year
    if (now.month, now.day) < (dob.month, dob.day):
        age -= 1
    return age


async def _create_alert_for_risk(
    db: AsyncSession,
    capture_event: CaptureEvent,
    risk_event: RiskEvent,
    classification: RiskClassification,
) -> Alert | None:
    """Create a portal alert for a risk event. Returns the created Alert."""
    category_meta = RISK_CATEGORIES.get(classification.category, {})
    description = category_meta.get("description", classification.category)

    title = f"{classification.severity.upper()} risk: {description}"
    body = (
        f"Detected {classification.category} ({classification.severity}) "
        f"on {capture_event.platform} with {classification.confidence:.0%} confidence. "
        f"{classification.reasoning}"
    )

    return await create_alert(
        db=db,
        data=AlertCreate(
            group_id=capture_event.group_id,
            member_id=capture_event.member_id,
            risk_event_id=risk_event.id,
            severity=classification.severity,
            title=title[:500],
            body=body[:2000],
            channel="portal",
        ),
    )
