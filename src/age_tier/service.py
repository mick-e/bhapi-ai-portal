"""Age tier service — business logic for tier assignment and permission queries."""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier.models import AgeTierConfig
from src.age_tier.rules import (
    AgeTier,
    age_from_dob,
    get_permissions,
    get_tier_for_age,
)
from src.age_tier.schemas import AgeTierConfigCreate
from src.exceptions import ForbiddenError, NotFoundError, ValidationError
from src.groups import GroupMember
from src.schemas import GroupContext

logger = structlog.get_logger()


async def _verify_member_ownership(
    db: AsyncSession,
    member_id: UUID,
    auth: GroupContext,
) -> None:
    """Verify that member_id belongs to the authenticated user's group.

    Raises ForbiddenError if the member does not belong to the user's group.
    """
    result = await db.execute(
        select(GroupMember).where(GroupMember.id == member_id)
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise NotFoundError("Group member", str(member_id))
    if auth.group_id is not None and member.group_id != auth.group_id:
        raise ForbiddenError("Member does not belong to your group")


async def assign_tier(
    db: AsyncSession,
    data: AgeTierConfigCreate,
    auth: GroupContext | None = None,
) -> AgeTierConfig:
    """Assign or update the age tier for a member (upsert).

    Calculates the tier from date_of_birth. Raises ValidationError
    if the age falls outside all tiers (< 5 or > 15).
    Raises ForbiddenError if auth is provided and the member
    does not belong to the authenticated user's group.
    """
    if auth is not None:
        await _verify_member_ownership(db, data.member_id, auth)

    age = age_from_dob(data.date_of_birth)
    tier = get_tier_for_age(age)

    if tier is None:
        raise ValidationError(
            f"Age {age} is outside the supported range (5-15). "
            "Cannot assign an age tier."
        )

    # Check for existing config (upsert)
    result = await db.execute(
        select(AgeTierConfig).where(AgeTierConfig.member_id == data.member_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.tier = tier.value
        existing.date_of_birth = data.date_of_birth
        existing.jurisdiction = data.jurisdiction
        existing.feature_overrides = data.feature_overrides or {}
        existing.locked_features = data.locked_features or []
        await db.flush()
        logger.info(
            "age_tier_updated",
            member_id=str(data.member_id),
            tier=tier.value,
            age=age,
        )
        return existing

    config = AgeTierConfig(
        member_id=data.member_id,
        tier=tier.value,
        date_of_birth=data.date_of_birth,
        jurisdiction=data.jurisdiction,
        feature_overrides=data.feature_overrides or {},
        locked_features=data.locked_features or [],
    )
    db.add(config)
    await db.flush()
    logger.info(
        "age_tier_assigned",
        member_id=str(data.member_id),
        tier=tier.value,
        age=age,
    )
    return config


async def get_member_tier(
    db: AsyncSession,
    member_id: UUID,
    auth: GroupContext | None = None,
) -> AgeTierConfig:
    """Get the age tier config for a member. Raises NotFoundError if not found.

    Raises ForbiddenError if auth is provided and the member
    does not belong to the authenticated user's group.
    """
    if auth is not None:
        await _verify_member_ownership(db, member_id, auth)

    result = await db.execute(
        select(AgeTierConfig).where(AgeTierConfig.member_id == member_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise NotFoundError("Age tier config", str(member_id))
    return config


async def get_member_permissions(
    db: AsyncSession,
    member_id: UUID,
    auth: GroupContext | None = None,
) -> dict:
    """Get the effective permissions for a member.

    Raises NotFoundError if the member has no tier config.
    Raises ForbiddenError if auth is provided and the member
    does not belong to the authenticated user's group.
    """
    config = await get_member_tier(db, member_id, auth=auth)
    tier = AgeTier(config.tier)
    return get_permissions(
        tier,
        feature_overrides=config.feature_overrides,
        locked_features=config.locked_features,
    )
