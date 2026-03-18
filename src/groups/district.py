"""District-level management for school pilot programs."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, func, String, DateTime, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.exceptions import NotFoundError, ConflictError, ValidationError
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()


class District(Base, UUIDMixin, TimestampMixin):
    """A school district containing multiple schools."""

    __tablename__ = "districts"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    admin_email: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="US")
    settings: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DistrictSchool(Base, UUIDMixin, TimestampMixin):
    """Links a school group to a district."""

    __tablename__ = "district_schools"

    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True
    )
    school_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pilot_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # pilot, active, inactive
    student_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


async def create_district(
    db: AsyncSession,
    name: str,
    admin_email: str,
    code: str | None = None,
    state: str | None = None,
    country: str = "US",
) -> District:
    """Create a new district."""
    if code:
        existing = await db.execute(
            select(District).where(District.code == code)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"District with code '{code}' already exists")

    district = District(
        id=uuid.uuid4(),
        name=name,
        code=code,
        admin_email=admin_email,
        state=state,
        country=country,
        active=True,
    )
    db.add(district)
    await db.flush()
    await db.refresh(district)
    logger.info("district_created", district_id=str(district.id), name=name)
    return district


async def add_school_to_district(
    db: AsyncSession,
    district_id: uuid.UUID,
    group_id: uuid.UUID,
    school_name: str,
    student_count: int = 0,
) -> DistrictSchool:
    """Add a school group to a district."""
    # Verify district exists
    d_result = await db.execute(select(District).where(District.id == district_id))
    if not d_result.scalar_one_or_none():
        raise NotFoundError("District", str(district_id))

    link = DistrictSchool(
        id=uuid.uuid4(),
        district_id=district_id,
        group_id=group_id,
        school_name=school_name,
        pilot_status="pilot",
        student_count=student_count,
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)
    logger.info("school_added_to_district", district_id=str(district_id), group_id=str(group_id))
    return link


async def get_district(db: AsyncSession, district_id: uuid.UUID) -> District:
    """Get a district by ID."""
    result = await db.execute(select(District).where(District.id == district_id))
    district = result.scalar_one_or_none()
    if not district:
        raise NotFoundError("District", str(district_id))
    return district


async def list_district_schools(
    db: AsyncSession, district_id: uuid.UUID
) -> list[DistrictSchool]:
    """List all schools in a district."""
    result = await db.execute(
        select(DistrictSchool).where(DistrictSchool.district_id == district_id)
    )
    return list(result.scalars().all())


async def get_district_summary(db: AsyncSession, district_id: uuid.UUID) -> dict:
    """Get summary stats for a district."""
    schools = await list_district_schools(db, district_id)
    total_students = sum(s.student_count for s in schools)
    pilot_count = sum(1 for s in schools if s.pilot_status == "pilot")

    return {
        "district_id": str(district_id),
        "total_schools": len(schools),
        "pilot_schools": pilot_count,
        "active_schools": sum(1 for s in schools if s.pilot_status == "active"),
        "total_students": total_students,
        "schools": [
            {
                "id": str(s.id),
                "group_id": str(s.group_id),
                "school_name": s.school_name,
                "pilot_status": s.pilot_status,
                "student_count": s.student_count,
            }
            for s in schools
        ],
    }
