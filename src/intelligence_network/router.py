"""Intelligence Network FastAPI router."""

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import get_current_user
from src.database import get_db
from src.dependencies import resolve_group_id
from src.intelligence_network import service
from src.intelligence_network.schemas import (
    ContributeSignalRequest,
    SignalFeedbackRequest,
    SubscriptionCreate,
    SubscriptionResponse,
    ThreatSignalResponse,
)
from src.schemas import GroupContext

logger = structlog.get_logger()

router = APIRouter()


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------


@router.post("/subscribe", response_model=SubscriptionResponse, status_code=201)
async def subscribe_to_network(
    data: SubscriptionCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Opt in to the intelligence network to receive anonymized threat signals."""
    group_id = resolve_group_id(None, auth)
    sub = await service.subscribe(
        db,
        group_id=group_id,
        signal_types=data.signal_types,
        min_severity=data.minimum_severity,
    )
    return sub


@router.delete("/subscribe", status_code=204)
async def unsubscribe_from_network(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Opt out of the intelligence network."""
    group_id = resolve_group_id(None, auth)
    await service.unsubscribe(db, group_id=group_id)


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current subscription status."""
    from sqlalchemy import select

    from src.intelligence_network.models import NetworkSubscription

    group_id = resolve_group_id(None, auth)
    result = await db.execute(
        select(NetworkSubscription).where(NetworkSubscription.group_id == group_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        from src.exceptions import NotFoundError
        raise NotFoundError("No subscription found. Subscribe first.")
    return sub


# ---------------------------------------------------------------------------
# Signal feed
# ---------------------------------------------------------------------------


@router.get("/feed", response_model=list[ThreatSignalResponse])
async def get_signal_feed(
    limit: int = Query(default=50, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch anonymized threat signals filtered by subscription preferences."""
    group_id = resolve_group_id(None, auth)
    return await service.fetch_signals_for_subscriber(db, group_id=group_id, limit=limit)


# ---------------------------------------------------------------------------
# Contribute
# ---------------------------------------------------------------------------


@router.post("/contribute", response_model=ThreatSignalResponse, status_code=201)
async def contribute_signal(
    data: ContributeSignalRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Contribute an anonymized threat signal to the network."""
    group_id = resolve_group_id(None, auth)
    raw_event = data.model_dump(exclude_none=True)
    signal = await service.contribute_signal(db, group_id=group_id, raw_event=raw_event)
    return signal


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


@router.post("/feedback", status_code=200)
async def submit_feedback(
    data: SignalFeedbackRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a signal as helpful or false-positive."""
    group_id = resolve_group_id(None, auth)
    await service.submit_feedback(
        db,
        signal_id=data.signal_id,
        group_id=group_id,
        is_helpful=data.is_helpful,
        notes=data.notes,
    )
    return {"status": "feedback_recorded"}
