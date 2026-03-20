"""Age verification service using Yoti."""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError
from src.groups.models import GroupMember

logger = structlog.get_logger()


async def start_age_verification(db: AsyncSession, group_id: UUID, member_id: UUID) -> dict:
    """Start a Yoti age verification flow for a member."""
    result = await db.execute(
        select(GroupMember).where(GroupMember.id == member_id, GroupMember.group_id == group_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError("Member", str(member_id))

    from src.integrations.yoti import create_age_verification_session
    session = await create_age_verification_session(str(member_id))

    logger.info("age_verification_started", member_id=str(member_id))
    return session


async def process_age_verification_result(
    db: AsyncSession, group_id: UUID, member_id: UUID, session_id: str
) -> dict:
    """Process the result of a Yoti age verification."""
    from src.integrations.yoti import get_age_verification_result
    result = await get_age_verification_result(session_id)

    if result.get("verified") and result.get("age") is not None:
        member_result = await db.execute(
            select(GroupMember).where(GroupMember.id == member_id, GroupMember.group_id == group_id)
        )
        member = member_result.scalar_one_or_none()
        if member:
            from datetime import datetime, timezone

            from dateutil.relativedelta import relativedelta
            now = datetime.now(timezone.utc)
            member.date_of_birth = now - relativedelta(years=result["age"])
            await db.flush()
            logger.info("age_verified", member_id=str(member_id), age=result["age"])

    return result
