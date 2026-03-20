"""Onboarding progress tracking for new users."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import Boolean, DateTime, Integer, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()

ONBOARDING_STEPS = [
    {
        "key": "create_group",
        "title": "Create your group",
        "description": "Set up a family, school, or club group",
    },
    {
        "key": "add_members",
        "title": "Add members",
        "description": "Invite family members or students",
    },
    {
        "key": "install_extension",
        "title": "Install extension",
        "description": "Install the browser extension on devices",
    },
    {
        "key": "configure_safety",
        "title": "Configure safety",
        "description": "Set safety levels and alert preferences",
    },
    {
        "key": "first_alert_review",
        "title": "Review first alert",
        "description": "Review and action your first safety alert",
    },
]


class OnboardingProgress(Base, UUIDMixin, TimestampMixin):
    """Tracks onboarding progress for a user."""

    __tablename__ = "onboarding_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_steps: Mapped[list | None] = mapped_column(JSONType, nullable=True, default=list)
    dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


async def get_onboarding_progress(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Get onboarding progress for a user."""
    result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.user_id == user_id)
    )
    progress = result.scalar_one_or_none()

    completed_steps = progress.completed_steps if progress else []
    current_step = progress.current_step if progress else 0
    dismissed = progress.dismissed if progress else False
    is_complete = progress.completed_at is not None if progress else False

    steps_with_status = []
    for i, step in enumerate(ONBOARDING_STEPS):
        steps_with_status.append({
            **step,
            "completed": step["key"] in (completed_steps or []),
            "current": i == current_step and not is_complete,
        })

    return {
        "user_id": str(user_id),
        "steps": steps_with_status,
        "current_step": current_step,
        "total_steps": len(ONBOARDING_STEPS),
        "completed_count": len(completed_steps or []),
        "is_complete": is_complete,
        "dismissed": dismissed,
    }


async def complete_onboarding_step(
    db: AsyncSession, user_id: uuid.UUID, step_key: str
) -> dict:
    """Mark an onboarding step as complete."""
    valid_keys = [s["key"] for s in ONBOARDING_STEPS]
    if step_key not in valid_keys:
        from src.exceptions import ValidationError
        raise ValidationError(f"Invalid step key: {step_key}")

    result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.user_id == user_id)
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = OnboardingProgress(
            id=uuid.uuid4(),
            user_id=user_id,
            current_step=0,
            completed_steps=[],
            dismissed=False,
        )
        db.add(progress)
        await db.flush()

    completed = list(progress.completed_steps or [])
    if step_key not in completed:
        completed.append(step_key)
    # Assign a new list to trigger SQLAlchemy change detection
    progress.completed_steps = list(completed)

    # Advance current step
    step_idx = valid_keys.index(step_key)
    if step_idx >= progress.current_step:
        progress.current_step = min(step_idx + 1, len(ONBOARDING_STEPS) - 1)

    # Check if all complete
    if len(completed) == len(ONBOARDING_STEPS):
        progress.completed_at = datetime.now(timezone.utc)

    await db.flush()
    logger.info("onboarding_step_completed", user_id=str(user_id), step=step_key)
    return await get_onboarding_progress(db, user_id)


async def dismiss_onboarding(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Dismiss onboarding wizard."""
    result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.user_id == user_id)
    )
    progress = result.scalar_one_or_none()
    if not progress:
        progress = OnboardingProgress(
            id=uuid.uuid4(),
            user_id=user_id,
            current_step=0,
            completed_steps=[],
            dismissed=True,
        )
        db.add(progress)
    else:
        progress.dismissed = True
    await db.flush()
    return await get_onboarding_progress(db, user_id)
