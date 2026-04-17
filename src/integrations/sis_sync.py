"""Common SIS roster sync logic."""

from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.groups import ClassGroup, ClassGroupMember, GroupMember

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


async def sync_sections_to_class_groups(
    db: AsyncSession,
    group_id: UUID,
    sections: list[dict],
) -> dict:
    """Map SIS sections to ClassGroup records.

    Each section dict should have:
      - name: str (section/class name)
      - grade_level: str | None
      - academic_year: str | None
      - students: list[str] (display names of students already in GroupMembers)
    """
    # Load existing class groups for this school
    result = await db.execute(
        select(ClassGroup).where(ClassGroup.group_id == group_id)
    )
    existing_classes = {cg.name: cg for cg in result.scalars().all()}

    # Load all group members for name-based matching
    result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id)
    )
    members_by_name = {m.display_name: m for m in result.scalars().all()}

    classes_created = 0
    classes_updated = 0
    members_assigned = 0

    for section in sections:
        section_name = section.get("name", "").strip()
        if not section_name:
            continue

        # Create or update class group
        if section_name in existing_classes:
            class_group = existing_classes[section_name]
            class_group.grade_level = section.get("grade_level")
            class_group.academic_year = section.get("academic_year")
            classes_updated += 1
        else:
            class_group = ClassGroup(
                id=uuid4(),
                group_id=group_id,
                name=section_name,
                grade_level=section.get("grade_level"),
                academic_year=section.get("academic_year"),
            )
            db.add(class_group)
            await db.flush()
            existing_classes[section_name] = class_group
            classes_created += 1

        # Load existing class members for dedup
        result = await db.execute(
            select(ClassGroupMember).where(
                ClassGroupMember.class_group_id == class_group.id
            )
        )
        existing_member_ids = {cm.member_id for cm in result.scalars().all()}

        # Assign students to the class group
        for student_name in section.get("students", []):
            member = members_by_name.get(student_name)
            if not member:
                continue
            if member.id in existing_member_ids:
                continue

            class_member = ClassGroupMember(
                id=uuid4(),
                class_group_id=class_group.id,
                member_id=member.id,
            )
            db.add(class_member)
            members_assigned += 1

    await db.flush()

    logger.info(
        "sis_sections_synced",
        group_id=str(group_id),
        classes_created=classes_created,
        classes_updated=classes_updated,
        members_assigned=members_assigned,
    )
    return {
        "classes_created": classes_created,
        "classes_updated": classes_updated,
        "members_assigned": members_assigned,
    }
