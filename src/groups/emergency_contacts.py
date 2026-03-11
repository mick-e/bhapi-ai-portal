"""Emergency Contact Integration — model + service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import Boolean, DateTime, ForeignKey, String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.exceptions import NotFoundError, ValidationError
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class EmergencyContact(Base, UUIDMixin, TimestampMixin):
    """An emergency contact for a family group."""

    __tablename__ = "emergency_contacts"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notify_on: Mapped[list] = mapped_column(JSONType, default=list)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

VALID_NOTIFY_TYPES = {"critical", "self_harm", "csam_adjacent"}
VALID_RELATIONSHIPS = {
    "grandparent",
    "school_counselor",
    "trusted_adult",
    "aunt_uncle",
    "family_friend",
    "therapist",
    "other",
}


async def add_emergency_contact(
    db: AsyncSession,
    group_id: uuid.UUID,
    data: dict,
) -> EmergencyContact:
    """Create a new emergency contact."""
    if not data.get("name"):
        raise ValidationError("Contact name is required")
    if not data.get("phone") and not data.get("email"):
        raise ValidationError("At least one of phone or email is required")

    notify_on = data.get("notify_on", [])
    invalid = set(notify_on) - VALID_NOTIFY_TYPES
    if invalid:
        raise ValidationError(f"Invalid notify_on types: {', '.join(invalid)}")

    contact = EmergencyContact(
        id=uuid.uuid4(),
        group_id=group_id,
        name=data["name"],
        relationship=data.get("relationship", "trusted_adult"),
        phone=data.get("phone"),
        email=data.get("email"),
        notify_on=notify_on,
        consent_given=data.get("consent_given", False),
        consent_given_at=(
            datetime.now(timezone.utc) if data.get("consent_given") else None
        ),
    )
    db.add(contact)
    await db.flush()
    await db.refresh(contact)

    logger.info(
        "emergency_contact_added",
        contact_id=str(contact.id),
        group_id=str(group_id),
    )
    return contact


async def update_emergency_contact(
    db: AsyncSession,
    contact_id: uuid.UUID,
    data: dict,
) -> EmergencyContact:
    """Update an emergency contact."""
    result = await db.execute(
        select(EmergencyContact).where(EmergencyContact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise NotFoundError("Emergency contact", str(contact_id))

    for field in ("name", "relationship", "phone", "email"):
        if field in data:
            setattr(contact, field, data[field])

    if "notify_on" in data:
        invalid = set(data["notify_on"]) - VALID_NOTIFY_TYPES
        if invalid:
            raise ValidationError(f"Invalid notify_on types: {', '.join(invalid)}")
        contact.notify_on = data["notify_on"]

    if "consent_given" in data:
        contact.consent_given = data["consent_given"]
        if data["consent_given"] and not contact.consent_given_at:
            contact.consent_given_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(contact)

    logger.info("emergency_contact_updated", contact_id=str(contact_id))
    return contact


async def remove_emergency_contact(
    db: AsyncSession,
    contact_id: uuid.UUID,
) -> None:
    """Delete an emergency contact."""
    result = await db.execute(
        select(EmergencyContact).where(EmergencyContact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise NotFoundError("Emergency contact", str(contact_id))

    await db.delete(contact)
    await db.flush()

    logger.info("emergency_contact_removed", contact_id=str(contact_id))


async def list_emergency_contacts(
    db: AsyncSession,
    group_id: uuid.UUID,
) -> list[EmergencyContact]:
    """List all emergency contacts for a group."""
    result = await db.execute(
        select(EmergencyContact)
        .where(EmergencyContact.group_id == group_id)
        .order_by(EmergencyContact.created_at)
    )
    return list(result.scalars().all())


async def notify_emergency_contacts(
    db: AsyncSession,
    group_id: uuid.UUID,
    alert: dict,
) -> int:
    """Send SMS/email to matching emergency contacts for a critical alert.

    Returns the number of contacts notified.
    """
    severity = alert.get("severity", "")
    contacts = await list_emergency_contacts(db, group_id)

    notified = 0
    for contact in contacts:
        if not contact.consent_given:
            continue

        # Check if this contact should be notified for the alert type
        notify_types = contact.notify_on or []
        should_notify = severity in notify_types or "critical" in notify_types

        if not should_notify:
            continue

        # Send SMS if phone available
        if contact.phone:
            try:
                from src.sms import send_sms

                await send_sms(
                    to=contact.phone,
                    body=(
                        f"Bhapi Safety Alert: {alert.get('title', 'Critical alert')} — "
                        f"Please check the Bhapi portal for details."
                    ),
                )
                notified += 1
            except Exception as exc:
                logger.warning(
                    "emergency_sms_failed",
                    contact_id=str(contact.id),
                    error=str(exc),
                )

        # Send email if available
        if contact.email:
            try:
                from src.email import send_email

                await send_email(
                    to=contact.email,
                    subject=f"Bhapi Safety Alert: {alert.get('title', 'Critical alert')}",
                    body=(
                        f"A critical safety alert has been triggered for a family member.\n\n"
                        f"Alert: {alert.get('title', '')}\n"
                        f"Details: {alert.get('body', '')}\n\n"
                        f"Please check the Bhapi portal or contact the family for details."
                    ),
                )
                notified += 1
            except Exception as exc:
                logger.warning(
                    "emergency_email_failed",
                    contact_id=str(contact.id),
                    error=str(exc),
                )

    logger.info(
        "emergency_contacts_notified",
        group_id=str(group_id),
        contacts_notified=notified,
    )
    return notified
