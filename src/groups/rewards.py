"""AI Usage Allowance Rewards — trigger evaluation and badge management."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

import structlog

from src.database import Base
from src.exceptions import NotFoundError
from src.models import TimestampMixin, UUIDMixin

logger = structlog.get_logger()


class Reward(Base, UUIDMixin, TimestampMixin):
    """An earned reward for a group member."""

    __tablename__ = "rewards"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False, index=True
    )
    reward_type: Mapped[str] = mapped_column(String(50), nullable=False)  # extra_time, badge
    trigger: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_description: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)  # minutes for extra_time, tier for badge
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    redeemed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


REWARD_TRIGGERS = {
    "literacy_module_complete": {
        "type": "extra_time",
        "value": 15,
        "description": "Completed an AI literacy module",
    },
    "safety_score_above_80": {
        "type": "extra_time",
        "value": 30,
        "description": "Maintained safety score above 80 for a week",
    },
    "week_no_high_risk": {
        "type": "badge",
        "value": 1,
        "description": "No high-severity risk events for a week",
    },
    "agreement_compliance_week": {
        "type": "extra_time",
        "value": 20,
        "description": "Followed family AI agreement for a week",
    },
}

BADGE_NAMES = {
    1: "Safety Star",
    2: "Digital Citizen",
    3: "AI Expert",
}


async def check_and_award_rewards(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID
) -> list[Reward]:
    """Evaluate triggers and award earned rewards.

    Checks each trigger condition and creates a reward if:
    - The condition is met
    - The same trigger hasn't already been awarded this week
    """
    awarded = []
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    for trigger_name, trigger_config in REWARD_TRIGGERS.items():
        # Check if already awarded this week
        existing = await db.execute(
            select(func.count(Reward.id)).where(
                Reward.group_id == group_id,
                Reward.member_id == member_id,
                Reward.trigger == trigger_name,
                Reward.earned_at >= week_ago,
            )
        )
        if (existing.scalar() or 0) > 0:
            continue

        # Evaluate trigger
        earned = await _evaluate_trigger(db, group_id, member_id, trigger_name)
        if not earned:
            continue

        # Award the reward
        reward = Reward(
            id=uuid.uuid4(),
            group_id=group_id,
            member_id=member_id,
            reward_type=trigger_config["type"],
            trigger=trigger_name,
            trigger_description=trigger_config["description"],
            value=trigger_config["value"],
            earned_at=now,
            expires_at=now + timedelta(days=30) if trigger_config["type"] == "extra_time" else None,
            redeemed=False,
        )
        db.add(reward)
        awarded.append(reward)

        logger.info(
            "reward_awarded",
            group_id=str(group_id),
            member_id=str(member_id),
            trigger=trigger_name,
            reward_type=trigger_config["type"],
            value=trigger_config["value"],
        )

    if awarded:
        await db.flush()
        for r in awarded:
            await db.refresh(r)

    return awarded


async def _evaluate_trigger(
    db: AsyncSession,
    group_id: uuid.UUID,
    member_id: uuid.UUID,
    trigger_name: str,
) -> bool:
    """Evaluate whether a specific trigger condition is met."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    if trigger_name == "literacy_module_complete":
        try:
            from src.literacy.models import LiteracyAssessment

            result = await db.execute(
                select(func.count(LiteracyAssessment.id)).where(
                    LiteracyAssessment.group_id == group_id,
                    LiteracyAssessment.member_id == member_id,
                    LiteracyAssessment.completed_at >= week_ago,
                )
            )
            return (result.scalar() or 0) > 0
        except Exception:
            return False

    elif trigger_name == "safety_score_above_80":
        try:
            from src.risk.models import RiskEvent

            result = await db.execute(
                select(func.count(RiskEvent.id)).where(
                    RiskEvent.group_id == group_id,
                    RiskEvent.member_id == member_id,
                    RiskEvent.created_at >= week_ago,
                )
            )
            risk_count = result.scalar() or 0
            # Safety score = 100 - (risk_count * 5), check if > 80
            return (100 - risk_count * 5) > 80
        except Exception:
            return False

    elif trigger_name == "week_no_high_risk":
        try:
            from src.risk.models import RiskEvent

            result = await db.execute(
                select(func.count(RiskEvent.id)).where(
                    RiskEvent.group_id == group_id,
                    RiskEvent.member_id == member_id,
                    RiskEvent.severity.in_(["high", "critical"]),
                    RiskEvent.created_at >= week_ago,
                )
            )
            return (result.scalar() or 0) == 0
        except Exception:
            return False

    elif trigger_name == "agreement_compliance_week":
        # Check that the member has been active (has events) but no blocking events
        try:
            from src.capture.models import CaptureEvent

            event_result = await db.execute(
                select(func.count(CaptureEvent.id)).where(
                    CaptureEvent.group_id == group_id,
                    CaptureEvent.member_id == member_id,
                    CaptureEvent.timestamp >= week_ago,
                )
            )
            has_activity = (event_result.scalar() or 0) > 0

            from src.blocking.models import BlockRule

            block_result = await db.execute(
                select(func.count(BlockRule.id)).where(
                    BlockRule.group_id == group_id,
                    BlockRule.member_id == member_id,
                    BlockRule.created_at >= week_ago,
                )
            )
            no_blocks = (block_result.scalar() or 0) == 0

            return has_activity and no_blocks
        except Exception:
            return False

    return False


async def list_rewards(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID
) -> list[Reward]:
    """List all rewards for a member, ordered by earned_at descending."""
    result = await db.execute(
        select(Reward)
        .where(
            Reward.group_id == group_id,
            Reward.member_id == member_id,
        )
        .order_by(Reward.earned_at.desc())
    )
    return list(result.scalars().all())


async def get_extra_time_minutes(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID
) -> int:
    """Get total unredeemed extra_time reward minutes.

    Only counts non-expired, unredeemed extra_time rewards.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(func.coalesce(func.sum(Reward.value), 0)).where(
            Reward.group_id == group_id,
            Reward.member_id == member_id,
            Reward.reward_type == "extra_time",
            Reward.redeemed == False,  # noqa: E712
            (Reward.expires_at.is_(None)) | (Reward.expires_at > now),
        )
    )
    return result.scalar() or 0


async def redeem_reward(db: AsyncSession, reward_id: uuid.UUID) -> Reward:
    """Mark a reward as redeemed."""
    result = await db.execute(select(Reward).where(Reward.id == reward_id))
    reward = result.scalar_one_or_none()
    if not reward:
        raise NotFoundError("Reward", str(reward_id))

    reward.redeemed = True
    await db.flush()
    await db.refresh(reward)

    logger.info("reward_redeemed", reward_id=str(reward_id))
    return reward


async def run_reward_check(db: AsyncSession) -> dict:
    """Daily job: evaluate reward triggers for all active members."""
    from src.groups.models import Group, GroupMember

    groups_result = await db.execute(select(Group))
    groups = list(groups_result.scalars().all())

    total_awarded = 0
    for group in groups:
        members_result = await db.execute(
            select(GroupMember).where(GroupMember.group_id == group.id)
        )
        members = list(members_result.scalars().all())
        for member in members:
            awarded = await check_and_award_rewards(db, group.id, member.id)
            total_awarded += len(awarded)

    return {"total_awarded": total_awarded, "groups_checked": len(groups)}
