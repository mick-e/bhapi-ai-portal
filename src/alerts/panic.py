"""Panic Button / Instant Report — child safety alert system."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, select, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.exceptions import NotFoundError, ValidationError
from src.models import TimestampMixin, UUIDMixin

logger = structlog.get_logger()


# ─── Model ───────────────────────────────────────────────────────────────────


class PanicReport(Base, UUIDMixin, TimestampMixin):
    """A panic report submitted by a child when they see something alarming."""

    __tablename__ = "panic_reports"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # scary_content, weird_request, bad_ai_response, other
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_response: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parent_responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


# ─── Constants ───────────────────────────────────────────────────────────────

VALID_CATEGORIES = ["scary_content", "weird_request", "bad_ai_response", "other"]

PARENT_QUICK_RESPONSES = [
    "I'm coming to talk to you right now",
    "Thank you for telling me. Let's discuss after school",
    "I'm glad you told me. You did the right thing",
    "Are you okay? I'll call you in a minute",
]


# ─── Service Functions ───────────────────────────────────────────────────────


async def create_panic_report(
    db: AsyncSession,
    group_id: uuid.UUID,
    member_id: uuid.UUID,
    category: str,
    message: str | None = None,
    platform: str | None = None,
    session_id: str | None = None,
) -> PanicReport:
    """Create a panic report and trigger critical alert + SMS to parents.

    This is the core child-safety flow: the child presses a panic button,
    a critical alert is created, and all parent members are notified via SMS.
    """
    if category not in VALID_CATEGORIES:
        raise ValidationError(
            f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}"
        )

    report = PanicReport(
        id=uuid.uuid4(),
        group_id=group_id,
        member_id=member_id,
        category=category,
        message=message,
        platform=platform,
        session_id=session_id,
        resolved=False,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)

    logger.info(
        "panic_report_created",
        report_id=str(report.id),
        member_id=str(member_id),
        category=category,
    )

    # Create a critical alert
    try:
        from src.alerts.service import create_alert
        from src.alerts.schemas import AlertCreate

        category_label = category.replace("_", " ").title()
        alert_body = f"Panic report: {category_label}"
        if message:
            alert_body += f" — {message[:200]}"

        await create_alert(
            db,
            AlertCreate(
                group_id=group_id,
                member_id=member_id,
                severity="critical",
                title="Panic Button Pressed",
                body=alert_body,
                channel="portal",
            ),
        )
    except Exception as exc:
        logger.error("panic_alert_creation_failed", error=str(exc))

    # Send SMS to all parent members
    try:
        from src.groups.models import GroupMember
        from src.auth.models import User

        # Get parent/admin members in the group
        parents_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.role.in_(["owner", "admin"]),
            )
        )
        parents = list(parents_result.scalars().all())

        # Get the child's name for the SMS
        child_result = await db.execute(
            select(GroupMember).where(GroupMember.id == member_id)
        )
        child = child_result.scalar_one_or_none()
        child_name = child.display_name if child else "A family member"

        category_label = category.replace("_", " ")
        sms_body = (
            f"BHAPI ALERT: {child_name} pressed the panic button "
            f"({category_label}). Please check the portal."
        )

        for parent in parents:
            if parent.user_id:
                user_result = await db.execute(
                    select(User).where(User.id == parent.user_id)
                )
                user = user_result.scalar_one_or_none()
                phone = getattr(user, "phone_number", None) if user else None
                if phone:
                    try:
                        from src.sms.service import send_sms
                        await send_sms(phone, sms_body)
                    except Exception as sms_err:
                        logger.warning(
                            "panic_sms_failed",
                            user_id=str(parent.user_id),
                            error=str(sms_err),
                        )
    except Exception as exc:
        logger.error("panic_sms_notification_failed", error=str(exc))

    return report


async def respond_to_panic(
    db: AsyncSession,
    report_id: uuid.UUID,
    user_id: uuid.UUID,
    response: str,
) -> PanicReport:
    """Parent responds to a panic report."""
    result = await db.execute(
        select(PanicReport).where(PanicReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise NotFoundError("PanicReport", str(report_id))

    report.parent_response = response[:500]
    report.parent_responded_at = datetime.now(timezone.utc)
    report.resolved = True

    await db.flush()
    await db.refresh(report)

    logger.info(
        "panic_report_responded",
        report_id=str(report_id),
        user_id=str(user_id),
    )
    return report


async def list_panic_reports(
    db: AsyncSession,
    group_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List panic reports for a group with pagination."""
    count_result = await db.execute(
        select(func.count(PanicReport.id)).where(
            PanicReport.group_id == group_id
        )
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(PanicReport)
        .where(PanicReport.group_id == group_id)
        .order_by(PanicReport.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    reports = list(result.scalars().all())

    total_pages = max((total + page_size - 1) // page_size, 1)

    return {
        "items": reports,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
