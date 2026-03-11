"""Family AI Agreement / Digital Contract — model + service."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import structlog
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class FamilyAgreement(Base, UUIDMixin, TimestampMixin):
    """A family AI agreement / digital contract."""

    __tablename__ = "family_agreements"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[str] = mapped_column(String(50), nullable=False)
    rules: Mapped[list] = mapped_column(JSONType, default=list)
    signed_by_parent: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    signed_by_parent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    signed_by_members: Mapped[list] = mapped_column(JSONType, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    review_due: Mapped[date] = mapped_column(Date, nullable=False)
    last_reviewed: Mapped[date | None] = mapped_column(Date, nullable=True)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

AGREEMENT_TEMPLATES: dict[str, dict] = {
    "ages_7_10": {
        "title": "Family AI Rules (Ages 7-10)",
        "rules": [
            {"category": "platforms", "text": "I will only use AI tools my parent has approved"},
            {"category": "time", "text": "I will use AI for no more than 30 minutes per day"},
            {"category": "content", "text": "I will not share my name, school, or address with AI"},
            {"category": "safety", "text": "I will tell my parent if AI says something that scares or confuses me"},
            {"category": "honesty", "text": "I will not use AI to do my homework for me"},
            {"category": "supervision", "text": "I will use AI in a shared family space"},
        ],
    },
    "ages_11_13": {
        "title": "Family AI Rules (Ages 11-13)",
        "rules": [
            {"category": "platforms", "text": "I will only use AI tools my parent knows about"},
            {"category": "time", "text": "I will limit my AI use to 1 hour per day"},
            {"category": "content", "text": "I will not share personal information with AI"},
            {"category": "safety", "text": "I will report any concerning AI interactions to my parent"},
            {"category": "honesty", "text": "I will use AI to help me learn, not to do my work for me"},
            {"category": "privacy", "text": "I will not share AI conversations that include family information"},
        ],
    },
    "ages_14_16": {
        "title": "Family AI Agreement (Ages 14-16)",
        "rules": [
            {"category": "platforms", "text": "I will discuss new AI platforms with my parent before using them"},
            {"category": "time", "text": "I will manage my AI usage responsibly"},
            {"category": "content", "text": "I understand the risks of sharing personal data with AI"},
            {"category": "safety", "text": "I will flag concerning content and discuss it with my parent"},
            {"category": "honesty", "text": "I will cite AI assistance in schoolwork when required"},
            {"category": "critical_thinking", "text": "I will verify important AI-generated information"},
        ],
    },
    "ages_17_plus": {
        "title": "Family AI Guidelines (Ages 17+)",
        "rules": [
            {"category": "awareness", "text": "I understand AI limitations and potential biases"},
            {"category": "privacy", "text": "I will protect my personal and family data when using AI"},
            {"category": "honesty", "text": "I will be transparent about AI use in academic and professional work"},
            {"category": "safety", "text": "I will report any AI-related safety concerns"},
        ],
    },
}


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def get_templates() -> dict[str, dict]:
    """Return all available agreement templates."""
    return AGREEMENT_TEMPLATES


async def create_agreement(
    db: AsyncSession,
    group_id: uuid.UUID,
    template_id: str,
    user_id: uuid.UUID,
) -> FamilyAgreement:
    """Create a new agreement from a template."""
    template = AGREEMENT_TEMPLATES.get(template_id)
    if not template:
        raise ValidationError(f"Unknown template: {template_id}")

    # Deactivate any existing active agreement
    existing = await get_active_agreement(db, group_id)
    if existing:
        existing.active = False
        await db.flush()

    rules = [
        {"category": r["category"], "rule_text": r["text"], "enabled": True}
        for r in template["rules"]
    ]

    agreement = FamilyAgreement(
        id=uuid.uuid4(),
        group_id=group_id,
        title=template["title"],
        template_id=template_id,
        rules=rules,
        signed_by_parent=user_id,
        signed_by_parent_at=datetime.now(timezone.utc),
        signed_by_members=[],
        active=True,
        review_due=date.today() + timedelta(days=90),
        last_reviewed=None,
    )
    db.add(agreement)
    await db.flush()
    await db.refresh(agreement)

    logger.info(
        "agreement_created",
        agreement_id=str(agreement.id),
        group_id=str(group_id),
        template_id=template_id,
    )
    return agreement


async def update_agreement(
    db: AsyncSession,
    agreement_id: uuid.UUID,
    rules: list[dict],
) -> FamilyAgreement:
    """Update the rules of an agreement."""
    result = await db.execute(
        select(FamilyAgreement).where(FamilyAgreement.id == agreement_id)
    )
    agreement = result.scalar_one_or_none()
    if not agreement:
        raise NotFoundError("Agreement", str(agreement_id))

    agreement.rules = rules
    await db.flush()
    await db.refresh(agreement)

    logger.info("agreement_updated", agreement_id=str(agreement_id))
    return agreement


async def sign_agreement(
    db: AsyncSession,
    agreement_id: uuid.UUID,
    member_id: uuid.UUID,
    name: str,
) -> FamilyAgreement:
    """A family member signs the agreement."""
    result = await db.execute(
        select(FamilyAgreement).where(FamilyAgreement.id == agreement_id)
    )
    agreement = result.scalar_one_or_none()
    if not agreement:
        raise NotFoundError("Agreement", str(agreement_id))

    # Check for duplicate signature
    existing_signers = agreement.signed_by_members or []
    for s in existing_signers:
        if s.get("member_id") == str(member_id):
            raise ConflictError("Member has already signed this agreement")

    new_entry = {
        "member_id": str(member_id),
        "name": name,
        "signed_at": datetime.now(timezone.utc).isoformat(),
    }
    agreement.signed_by_members = [*existing_signers, new_entry]
    await db.flush()
    await db.refresh(agreement)

    logger.info(
        "agreement_signed",
        agreement_id=str(agreement_id),
        member_id=str(member_id),
    )
    return agreement


async def get_active_agreement(
    db: AsyncSession,
    group_id: uuid.UUID,
) -> FamilyAgreement | None:
    """Get the current active agreement for a group."""
    result = await db.execute(
        select(FamilyAgreement).where(
            FamilyAgreement.group_id == group_id,
            FamilyAgreement.active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def mark_reviewed(
    db: AsyncSession,
    agreement_id: uuid.UUID,
) -> FamilyAgreement:
    """Mark agreement as reviewed and set next review date."""
    result = await db.execute(
        select(FamilyAgreement).where(FamilyAgreement.id == agreement_id)
    )
    agreement = result.scalar_one_or_none()
    if not agreement:
        raise NotFoundError("Agreement", str(agreement_id))

    agreement.last_reviewed = date.today()
    agreement.review_due = date.today() + timedelta(days=90)
    await db.flush()
    await db.refresh(agreement)

    logger.info("agreement_reviewed", agreement_id=str(agreement_id))
    return agreement


# ---------------------------------------------------------------------------
# Background job: review reminder
# ---------------------------------------------------------------------------


async def agreement_review_reminder(db: AsyncSession) -> dict:
    """Check for agreements due for review and create alerts."""
    today = date.today()
    result = await db.execute(
        select(FamilyAgreement).where(
            FamilyAgreement.active.is_(True),
            FamilyAgreement.review_due <= today,
        )
    )
    agreements = list(result.scalars().all())

    reminded = 0
    for agreement in agreements:
        try:
            from src.alerts.schemas import AlertCreate

            alert_data = AlertCreate(
                group_id=agreement.group_id,
                severity="medium",
                title="Family AI Agreement Review Due",
                body=(
                    f'Your family AI agreement "{agreement.title}" is due for review. '
                    "Please review the rules with your family to ensure they are still appropriate."
                ),
                channel="portal",
            )
            from src.alerts.service import create_alert

            await create_alert(db, alert_data)
            reminded += 1
        except Exception as exc:
            logger.warning(
                "agreement_review_reminder_failed",
                agreement_id=str(agreement.id),
                error=str(exc),
            )

    logger.info("agreement_review_reminders_sent", count=reminded)
    return {"agreements_reminded": reminded}
