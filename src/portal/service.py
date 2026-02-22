"""Portal BFF service — aggregates data from other modules."""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.groups.models import Group, GroupMember
from src.portal.schemas import (
    AlertSummary,
    DashboardResponse,
    MemberStatus,
    SpendSummary,
)

logger = structlog.get_logger()


async def get_dashboard(db: AsyncSession, group_id: UUID, user_id: UUID) -> DashboardResponse:
    """Aggregate dashboard data for a group (FR-010)."""
    # Get group
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        from src.exceptions import NotFoundError
        raise NotFoundError("Group", str(group_id))

    # Get members
    members_result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id)
    )
    members = list(members_result.scalars().all())

    member_statuses = [
        MemberStatus(
            id=m.id,
            display_name=m.display_name,
            role=m.role,
            last_active=None,
            active_platforms=[],
            unresolved_alerts=0,
        )
        for m in members
    ]

    return DashboardResponse(
        group_id=group.id,
        group_name=group.name,
        active_members=0,
        total_members=len(members),
        recent_activity=[],
        alert_summary=AlertSummary(),
        spend_summary=SpendSummary(),
        members=member_statuses,
    )
