"""Common SIS roster sync logic."""

from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.groups.models import GroupMember

logger = structlog.get_logger()


async def sync_roster(
    db: AsyncSession,
    group_id: UUID,
    roster: list[dict],
) -> dict:
    """Sync SIS roster records to GroupMembers."""
    result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id)
    )
    existing = {m.display_name: m for m in result.scalars().all()}

    created = 0
    updated = 0

    for entry in roster:
        display_name = f"{entry['first_name']} {entry['last_name']}".strip()
        if not display_name:
            continue

        if display_name in existing:
            updated += 1
        else:
            member = GroupMember(
                id=uuid4(),
                group_id=group_id,
                role=entry.get("role", "member"),
                display_name=display_name,
            )
            db.add(member)
            created += 1

    await db.flush()

    logger.info("sis_sync_completed", group_id=str(group_id), created=created, updated=updated)
    return {"members_created": created, "members_updated": updated, "members_deactivated": 0}
