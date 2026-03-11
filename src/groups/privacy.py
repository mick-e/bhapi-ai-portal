"""Sibling privacy controls — visibility and child self-view management."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

import structlog

from src.database import Base
from src.exceptions import ForbiddenError, NotFoundError, ValidationError
from src.groups.models import Group, GroupMember
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()

# Allowed sections for child self-view
ALLOWED_SELF_VIEW_SECTIONS = ["safety_score", "time_usage", "literacy", "rewards"]
# Sections that are NEVER shown to children
FORBIDDEN_SELF_VIEW_SECTIONS = ["sibling_data", "raw_risk_events", "parent_alerts"]


class MemberVisibility(Base, UUIDMixin, TimestampMixin):
    """Controls which parents can see a specific child's data."""

    __tablename__ = "member_visibility"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False, index=True
    )
    visible_to: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )


class ChildSelfView(Base, UUIDMixin, TimestampMixin):
    """Controls whether a child can see their own dashboard."""

    __tablename__ = "child_self_views"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False, unique=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sections: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)


async def check_member_visibility(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID, member_id: uuid.UUID
) -> bool:
    """Check if a user can see a member's data.

    Returns True if:
    - No visibility rows exist for this member (default: all parents can see)
    - The user is explicitly in the visible_to list
    """
    # Count visibility rows for this member
    count_result = await db.execute(
        select(func.count(MemberVisibility.id)).where(
            MemberVisibility.group_id == group_id,
            MemberVisibility.member_id == member_id,
        )
    )
    total_rows = count_result.scalar() or 0

    # No visibility rows = default behavior (all parents can see)
    if total_rows == 0:
        return True

    # Check if user is in visible_to
    result = await db.execute(
        select(func.count(MemberVisibility.id)).where(
            MemberVisibility.group_id == group_id,
            MemberVisibility.member_id == member_id,
            MemberVisibility.visible_to == user_id,
        )
    )
    return (result.scalar() or 0) > 0


async def set_member_visibility(
    db: AsyncSession,
    group_id: uuid.UUID,
    member_id: uuid.UUID,
    visible_to_user_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    """Set which parents can see this child's data.

    If an empty list is provided, removes all visibility restrictions
    (reverts to default: all parents can see).
    """
    # Delete existing visibility rows for this member
    existing = await db.execute(
        select(MemberVisibility).where(
            MemberVisibility.group_id == group_id,
            MemberVisibility.member_id == member_id,
        )
    )
    for row in existing.scalars().all():
        await db.delete(row)

    # Create new visibility rows
    for user_id in visible_to_user_ids:
        vis = MemberVisibility(
            id=uuid.uuid4(),
            group_id=group_id,
            member_id=member_id,
            visible_to=user_id,
        )
        db.add(vis)

    await db.flush()

    logger.info(
        "member_visibility_set",
        group_id=str(group_id),
        member_id=str(member_id),
        visible_to_count=len(visible_to_user_ids),
    )
    return visible_to_user_ids


async def get_member_visibility(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID
) -> list[uuid.UUID]:
    """List parents who can see this member's data.

    Returns an empty list if no restrictions are set (all parents can see).
    """
    result = await db.execute(
        select(MemberVisibility.visible_to).where(
            MemberVisibility.group_id == group_id,
            MemberVisibility.member_id == member_id,
        )
    )
    return [row[0] for row in result.all()]


async def enable_child_self_view(
    db: AsyncSession,
    group_id: uuid.UUID,
    member_id: uuid.UUID,
    sections: list[str],
) -> ChildSelfView:
    """Enable self-view for a child with specific sections."""
    # Validate sections
    for section in sections:
        if section not in ALLOWED_SELF_VIEW_SECTIONS:
            raise ValidationError(
                f"Invalid section: '{section}'. Allowed: {ALLOWED_SELF_VIEW_SECTIONS}"
            )
        if section in FORBIDDEN_SELF_VIEW_SECTIONS:
            raise ValidationError(f"Section '{section}' is not allowed for child self-view")

    # Upsert the self-view config
    result = await db.execute(
        select(ChildSelfView).where(
            ChildSelfView.group_id == group_id,
            ChildSelfView.member_id == member_id,
        )
    )
    self_view = result.scalar_one_or_none()

    if self_view:
        self_view.enabled = True
        self_view.sections = sections
    else:
        self_view = ChildSelfView(
            id=uuid.uuid4(),
            group_id=group_id,
            member_id=member_id,
            enabled=True,
            sections=sections,
        )
        db.add(self_view)

    await db.flush()
    await db.refresh(self_view)

    logger.info(
        "child_self_view_enabled",
        group_id=str(group_id),
        member_id=str(member_id),
        sections=sections,
    )
    return self_view


async def disable_child_self_view(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID
) -> None:
    """Disable self-view for a child."""
    result = await db.execute(
        select(ChildSelfView).where(
            ChildSelfView.group_id == group_id,
            ChildSelfView.member_id == member_id,
        )
    )
    self_view = result.scalar_one_or_none()

    if self_view:
        self_view.enabled = False
        await db.flush()

    logger.info(
        "child_self_view_disabled",
        group_id=str(group_id),
        member_id=str(member_id),
    )


async def get_child_self_view(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID
) -> ChildSelfView | None:
    """Get the child self-view config."""
    result = await db.execute(
        select(ChildSelfView).where(
            ChildSelfView.group_id == group_id,
            ChildSelfView.member_id == member_id,
        )
    )
    return result.scalar_one_or_none()


async def get_child_dashboard(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID
) -> dict:
    """Build a filtered dashboard for a child's own view.

    Only includes allowed sections. NEVER includes other siblings' data,
    raw risk events, or parent alerts.
    """
    # Verify self-view is enabled
    self_view = await get_child_self_view(db, group_id, member_id)
    if not self_view or not self_view.enabled:
        raise ForbiddenError("Self-view is not enabled for this member")

    sections = self_view.sections or []
    dashboard: dict = {
        "member_id": str(member_id),
        "group_id": str(group_id),
        "sections": sections,
    }

    # Safety score section
    if "safety_score" in sections:
        try:
            from src.risk.models import RiskEvent
            from sqlalchemy import func as sqlfunc

            score_result = await db.execute(
                select(sqlfunc.count(RiskEvent.id)).where(
                    RiskEvent.group_id == group_id,
                    RiskEvent.member_id == member_id,
                )
            )
            risk_count = score_result.scalar() or 0
            # Simple safety score: 100 minus risk events (capped at 0)
            dashboard["safety_score"] = max(0, 100 - risk_count * 5)
        except Exception:
            dashboard["safety_score"] = 100

    # Time usage section
    if "time_usage" in sections:
        try:
            from src.capture.models import CaptureEvent
            from datetime import datetime, time, timezone

            today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
            time_result = await db.execute(
                select(func.count(CaptureEvent.id)).where(
                    CaptureEvent.group_id == group_id,
                    CaptureEvent.member_id == member_id,
                    CaptureEvent.timestamp >= today_start,
                )
            )
            dashboard["sessions_today"] = time_result.scalar() or 0
        except Exception:
            dashboard["sessions_today"] = 0

    # Literacy progress section
    if "literacy" in sections:
        try:
            from src.literacy.models import LiteracyProgress

            lit_result = await db.execute(
                select(LiteracyProgress).where(
                    LiteracyProgress.group_id == group_id,
                    LiteracyProgress.member_id == member_id,
                )
            )
            progress = lit_result.scalar_one_or_none()
            if progress:
                dashboard["literacy"] = {
                    "modules_completed": progress.modules_completed,
                    "current_level": progress.current_level,
                    "total_score": progress.total_score,
                }
            else:
                dashboard["literacy"] = {
                    "modules_completed": 0,
                    "current_level": "beginner",
                    "total_score": 0,
                }
        except Exception:
            dashboard["literacy"] = {
                "modules_completed": 0,
                "current_level": "beginner",
                "total_score": 0,
            }

    # Rewards section
    if "rewards" in sections:
        try:
            from src.groups.rewards import list_rewards, get_extra_time_minutes

            rewards = await list_rewards(db, group_id, member_id)
            extra_time = await get_extra_time_minutes(db, group_id, member_id)
            dashboard["rewards"] = {
                "items": [
                    {
                        "id": str(r.id),
                        "reward_type": r.reward_type,
                        "trigger_description": r.trigger_description,
                        "value": r.value,
                        "earned_at": r.earned_at.isoformat() if r.earned_at else None,
                        "redeemed": r.redeemed,
                    }
                    for r in rewards
                ],
                "extra_time_minutes": extra_time,
            }
        except Exception:
            dashboard["rewards"] = {"items": [], "extra_time_minutes": 0}

    return dashboard
