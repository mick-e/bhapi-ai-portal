"""Teacher dashboard and classroom management features."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, func, String, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.exceptions import NotFoundError
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()


class ParentTeacherNote(Base, UUIDMixin, TimestampMixin):
    """A communication between a parent and teacher about a student."""

    __tablename__ = "parent_teacher_notes"

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    author_role: Mapped[str] = mapped_column(String(20), nullable=False)  # teacher, parent
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reply_to_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


async def create_note(
    db: AsyncSession,
    group_id: uuid.UUID,
    member_id: uuid.UUID,
    author_id: uuid.UUID,
    author_role: str,
    subject: str,
    body: str,
    reply_to_id: uuid.UUID | None = None,
) -> ParentTeacherNote:
    """Create a parent-teacher communication note."""
    note = ParentTeacherNote(
        id=uuid.uuid4(),
        group_id=group_id,
        member_id=member_id,
        author_id=author_id,
        author_role=author_role,
        subject=subject,
        body=body,
        reply_to_id=reply_to_id,
    )
    db.add(note)
    await db.flush()
    await db.refresh(note)
    logger.info("parent_teacher_note_created", note_id=str(note.id))
    return note


async def list_notes_for_member(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID
) -> list[ParentTeacherNote]:
    """List all notes for a student/member."""
    result = await db.execute(
        select(ParentTeacherNote).where(
            ParentTeacherNote.group_id == group_id,
            ParentTeacherNote.member_id == member_id,
        ).order_by(ParentTeacherNote.created_at.desc())
    )
    return list(result.scalars().all())


async def mark_note_read(
    db: AsyncSession, note_id: uuid.UUID
) -> ParentTeacherNote:
    """Mark a note as read."""
    result = await db.execute(
        select(ParentTeacherNote).where(ParentTeacherNote.id == note_id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise NotFoundError("Note", str(note_id))
    note.read_at = datetime.now(timezone.utc)
    await db.flush()
    return note


async def get_teacher_dashboard(
    db: AsyncSession, group_id: uuid.UUID, teacher_id: uuid.UUID
) -> dict:
    """Get teacher dashboard data for a school group."""
    from src.groups.models import ClassGroup, ClassGroupMember
    from src.alerts.models import Alert

    # Get teacher's classes
    classes_result = await db.execute(
        select(ClassGroup).where(
            ClassGroup.group_id == group_id,
            ClassGroup.teacher_id == teacher_id,
        )
    )
    classes = list(classes_result.scalars().all())

    class_data = []
    for cls in classes:
        member_count_result = await db.execute(
            select(func.count(ClassGroupMember.id)).where(
                ClassGroupMember.class_group_id == cls.id
            )
        )
        member_count = member_count_result.scalar() or 0

        class_data.append({
            "id": str(cls.id),
            "name": cls.name,
            "grade_level": cls.grade_level,
            "member_count": member_count,
        })

    # Recent alerts for group
    alerts_result = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.group_id == group_id,
            Alert.status != "acknowledged",
        )
    )
    unread_alerts = alerts_result.scalar() or 0

    return {
        "teacher_id": str(teacher_id),
        "group_id": str(group_id),
        "classes": class_data,
        "total_classes": len(class_data),
        "unread_alerts": unread_alerts,
    }
