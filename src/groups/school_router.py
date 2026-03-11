"""School admin API endpoints."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription
from src.exceptions import ForbiddenError, NotFoundError, ValidationError
from src.groups.models import ClassGroup, ClassGroupMember, Group, GroupMember
from src.risk.models import RiskEvent
from src.schemas import BaseSchema, GroupContext

logger = structlog.get_logger()

router = APIRouter(dependencies=[Depends(require_active_trial_or_subscription)])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ClassGroupCreate(BaseSchema):
    """Create class group request."""

    name: str = Field(min_length=1, max_length=255)
    grade_level: str | None = Field(None, max_length=50)
    teacher_id: UUID | None = None
    academic_year: str | None = Field(None, max_length=20)


class ClassGroupResponse(BaseSchema):
    """Class group response."""

    id: UUID
    group_id: UUID
    name: str
    grade_level: str | None
    teacher_id: UUID | None
    academic_year: str | None
    member_count: int = 0
    created_at: datetime


class ClassMemberAdd(BaseSchema):
    """Add member to class request."""

    member_id: UUID


class ClassMemberResponse(BaseSchema):
    """Class member response."""

    id: UUID
    class_group_id: UUID
    member_id: UUID
    display_name: str
    created_at: datetime


class RiskEventResponse(BaseSchema):
    """Risk event response (simplified)."""

    id: UUID
    member_id: UUID
    category: str
    severity: str
    confidence: float
    created_at: datetime


class SafeguardingReportResponse(BaseSchema):
    """30-day safeguarding summary."""

    period_start: datetime
    period_end: datetime
    total_risks: int
    by_severity: dict[str, int]
    by_category: dict[str, int]
    flagged_students: list[dict]


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _verify_school_admin(
    db: AsyncSession, auth: GroupContext
) -> UUID:
    """Verify user is a school_admin and return group_id."""
    if not auth.group_id:
        raise ValidationError("No group found. Please create a group first.")

    result = await db.execute(
        select(Group).where(Group.id == auth.group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise NotFoundError("Group", str(auth.group_id))
    if group.type != "school":
        raise ForbiddenError("School admin features are only available for school groups")

    # Verify user is a school_admin member
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == auth.group_id,
            GroupMember.user_id == auth.user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member or member.role != "school_admin":
        raise ForbiddenError("Only school admins can manage classes")

    return auth.group_id


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/classes", response_model=list[ClassGroupResponse])
async def list_classes(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all classes in the school group with member counts."""
    group_id = await _verify_school_admin(db, auth)

    result = await db.execute(
        select(ClassGroup).where(ClassGroup.group_id == group_id)
    )
    classes = result.scalars().all()

    responses = []
    for cls in classes:
        # Count members via relationship
        member_count = len(cls.class_members) if cls.class_members else 0
        responses.append(ClassGroupResponse(
            id=cls.id,
            group_id=cls.group_id,
            name=cls.name,
            grade_level=cls.grade_level,
            teacher_id=cls.teacher_id,
            academic_year=cls.academic_year,
            member_count=member_count,
            created_at=cls.created_at,
        ))

    return responses


@router.post("/classes", response_model=ClassGroupResponse, status_code=201)
async def create_class(
    data: ClassGroupCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new class in the school group."""
    group_id = await _verify_school_admin(db, auth)

    class_group = ClassGroup(
        id=uuid4(),
        group_id=group_id,
        name=data.name,
        grade_level=data.grade_level,
        teacher_id=data.teacher_id,
        academic_year=data.academic_year,
    )
    db.add(class_group)
    await db.flush()
    await db.refresh(class_group, ["class_members"])

    logger.info("class_created", class_id=str(class_group.id), group_id=str(group_id))

    return ClassGroupResponse(
        id=class_group.id,
        group_id=class_group.group_id,
        name=class_group.name,
        grade_level=class_group.grade_level,
        teacher_id=class_group.teacher_id,
        academic_year=class_group.academic_year,
        member_count=0,
        created_at=class_group.created_at,
    )


@router.get("/classes/{class_id}/risks", response_model=list[RiskEventResponse])
async def get_class_risks(
    class_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get risk events for all members of a class."""
    group_id = await _verify_school_admin(db, auth)

    # Verify class belongs to the group
    result = await db.execute(
        select(ClassGroup).where(
            ClassGroup.id == class_id,
            ClassGroup.group_id == group_id,
        )
    )
    class_group = result.scalar_one_or_none()
    if not class_group:
        raise NotFoundError("Class", str(class_id))

    # Get member IDs in this class
    member_ids = [cm.member_id for cm in class_group.class_members]
    if not member_ids:
        return []

    # Get risk events for those members
    result = await db.execute(
        select(RiskEvent)
        .where(
            RiskEvent.group_id == group_id,
            RiskEvent.member_id.in_(member_ids),
        )
        .order_by(RiskEvent.created_at.desc())
        .limit(100)
    )
    risks = result.scalars().all()

    return [
        RiskEventResponse(
            id=r.id,
            member_id=r.member_id,
            category=r.category,
            severity=r.severity,
            confidence=r.confidence,
            created_at=r.created_at,
        )
        for r in risks
    ]


@router.post(
    "/classes/{class_id}/members",
    response_model=ClassMemberResponse,
    status_code=201,
)
async def add_class_member(
    class_id: UUID,
    data: ClassMemberAdd,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add an existing group member to a class."""
    group_id = await _verify_school_admin(db, auth)

    # Verify class belongs to group
    result = await db.execute(
        select(ClassGroup).where(
            ClassGroup.id == class_id,
            ClassGroup.group_id == group_id,
        )
    )
    class_group = result.scalar_one_or_none()
    if not class_group:
        raise NotFoundError("Class", str(class_id))

    # Verify member belongs to group
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.id == data.member_id,
            GroupMember.group_id == group_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError("Member", str(data.member_id))

    # Check if already in class
    result = await db.execute(
        select(ClassGroupMember).where(
            ClassGroupMember.class_group_id == class_id,
            ClassGroupMember.member_id == data.member_id,
        )
    )
    if result.scalar_one_or_none():
        raise ValidationError("Member is already in this class")

    class_member = ClassGroupMember(
        id=uuid4(),
        class_group_id=class_id,
        member_id=data.member_id,
    )
    db.add(class_member)
    await db.flush()

    logger.info(
        "class_member_added",
        class_id=str(class_id),
        member_id=str(data.member_id),
    )

    return ClassMemberResponse(
        id=class_member.id,
        class_group_id=class_member.class_group_id,
        member_id=class_member.member_id,
        display_name=member.display_name,
        created_at=class_member.created_at,
    )


@router.delete("/classes/{class_id}/members/{member_id}", status_code=204)
async def remove_class_member(
    class_id: UUID,
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from a class."""
    group_id = await _verify_school_admin(db, auth)

    # Verify class belongs to group
    result = await db.execute(
        select(ClassGroup).where(
            ClassGroup.id == class_id,
            ClassGroup.group_id == group_id,
        )
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Class", str(class_id))

    # Find and remove the class member
    result = await db.execute(
        select(ClassGroupMember).where(
            ClassGroupMember.class_group_id == class_id,
            ClassGroupMember.member_id == member_id,
        )
    )
    class_member = result.scalar_one_or_none()
    if not class_member:
        raise NotFoundError("Class member", str(member_id))

    await db.delete(class_member)
    await db.flush()

    logger.info(
        "class_member_removed",
        class_id=str(class_id),
        member_id=str(member_id),
    )
    return None


@router.get("/safeguarding-report", response_model=SafeguardingReportResponse)
async def get_safeguarding_report(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a 30-day safeguarding summary for the school."""
    group_id = await _verify_school_admin(db, auth)

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=30)

    # Get all risk events in the last 30 days for this group
    result = await db.execute(
        select(RiskEvent).where(
            RiskEvent.group_id == group_id,
            RiskEvent.created_at >= period_start,
        )
    )
    risks = result.scalars().all()

    # Aggregate by severity
    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    member_risk_counts: dict[UUID, int] = {}

    for risk in risks:
        by_severity[risk.severity] = by_severity.get(risk.severity, 0) + 1
        by_category[risk.category] = by_category.get(risk.category, 0) + 1
        member_risk_counts[risk.member_id] = member_risk_counts.get(risk.member_id, 0) + 1

    # Find flagged students (members with high/critical risks)
    flagged_member_ids = set()
    for risk in risks:
        if risk.severity in ("high", "critical"):
            flagged_member_ids.add(risk.member_id)

    flagged_students = []
    if flagged_member_ids:
        result = await db.execute(
            select(GroupMember).where(GroupMember.id.in_(flagged_member_ids))
        )
        members = result.scalars().all()
        for m in members:
            flagged_students.append({
                "member_id": str(m.id),
                "display_name": m.display_name,
                "risk_count": member_risk_counts.get(m.id, 0),
            })

    return SafeguardingReportResponse(
        period_start=period_start,
        period_end=now,
        total_risks=len(risks),
        by_severity=by_severity,
        by_category=by_category,
        flagged_students=flagged_students,
    )
