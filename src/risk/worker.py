"""Risk pipeline batch worker — processes unprocessed capture events.

Designed to run as a periodic background job (e.g., every 30 seconds).
Picks up capture events where risk_processed=False and content is non-null,
then runs each through the pipeline.
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.capture.models import CaptureEvent
from src.risk.pipeline import process_capture_event

logger = structlog.get_logger()

# Maximum events to process per batch run
DEFAULT_BATCH_SIZE = 50


async def process_backlog(
    db: AsyncSession,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    """Process a batch of unprocessed capture events.

    Returns the number of events processed.
    """
    # Find unprocessed events with content
    result = await db.execute(
        select(CaptureEvent)
        .where(
            CaptureEvent.risk_processed.is_(False),
            CaptureEvent.content.isnot(None),
            CaptureEvent.content != "",
        )
        .order_by(CaptureEvent.timestamp.asc())
        .limit(batch_size)
    )
    events = list(result.scalars().all())

    if not events:
        logger.debug("worker_no_pending_events")
        return 0

    processed = 0
    for event in events:
        try:
            await process_capture_event(db, event)
            processed += 1
        except Exception as exc:
            logger.error(
                "worker_event_error",
                event_id=str(event.id),
                error=str(exc),
            )
            # Mark as processed to prevent infinite retry loops
            event.risk_processed = True
            await db.flush()

    await db.commit()

    logger.info(
        "worker_batch_complete",
        total=len(events),
        processed=processed,
        failed=len(events) - processed,
    )

    return processed
