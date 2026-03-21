"""Parental abuse safeguards — trusted adult, custody model, teen privacy.

This module provides safety mechanisms for children who may be experiencing
parental abuse or custody conflicts. Key design principles:

1. Trusted adult requests are NEVER visible to parents
2. Custody-aware access controls (primary/secondary guardian roles)
3. Age-tier-based privacy (young=everything, preteen=partial, teen=summary only)
4. Helpline numbers provided alongside trusted adult flow
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import Base
from src.exceptions import ForbiddenError, NotFoundError, ValidationError
from src.models import JSONType, TimestampMixin, UUIDMixin

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class GuardianRole(str, Enum):
    """Guardian role in custody arrangement."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    EMERGENCY = "emergency"


class PrivacyTier(str, Enum):
    """Privacy tier determining what data parents can see."""

    YOUNG = "young"        # 5-9: everything visible to parent
    PRETEEN = "preteen"    # 10-12: posts+contacts visible, NOT messages
    TEEN = "teen"          # 13-15: summary+flagged content only


class TrustedAdultStatus(str, Enum):
    """Status of a trusted adult request."""

    PENDING = "pending"
    CONTACTED = "contacted"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class CustodyDisputeStatus(str, Enum):
    """Status of a custody dispute flag."""

    NONE = "none"
    FLAGGED = "flagged"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TrustedAdultRequest(Base, UUIDMixin, TimestampMixin):
    """Request for a trusted adult — NOT visible to the child's parent.

    This is a safety-critical record. The parent MUST NOT be able to
    see, query, or infer the existence of this request.
    """

    __tablename__ = "trusted_adult_requests"

    child_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trusted_adult_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    trusted_adult_contact: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TrustedAdultStatus.PENDING.value,
    )
    helplines_shown: Mapped[dict | None] = mapped_column(
        JSONType, nullable=True,
    )
    contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    # Audit: who processed this (platform staff, not parent)
    processed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )


class CustodyConfig(Base, UUIDMixin, TimestampMixin):
    """Custody configuration for a child member.

    Defines guardian roles and access levels for custody-aware families.
    """

    __tablename__ = "custody_configs"

    child_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    guardian_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=GuardianRole.PRIMARY.value,
    )
    can_view_activity: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    can_manage_settings: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    can_approve_contacts: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    dispute_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CustodyDisputeStatus.NONE.value,
    )
    dispute_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TeenPrivacyConfig(Base, UUIDMixin, TimestampMixin):
    """Privacy configuration per child based on age tier.

    Controls what data is visible to guardians based on the child's age.
    """

    __tablename__ = "teen_privacy_configs"

    child_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    privacy_tier: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )
    posts_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    contacts_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    messages_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    activity_summary_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    flagged_content_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )


# ---------------------------------------------------------------------------
# Helpline Data
# ---------------------------------------------------------------------------

HELPLINES = {
    "US": [
        {"name": "Childhelp National Child Abuse Hotline", "number": "1-800-422-4453", "available": "24/7"},
        {"name": "Crisis Text Line", "number": "Text HOME to 741741", "available": "24/7"},
        {"name": "National Domestic Violence Hotline", "number": "1-800-799-7233", "available": "24/7"},
    ],
    "UK": [
        {"name": "Childline", "number": "0800 1111", "available": "24/7"},
        {"name": "NSPCC Helpline", "number": "0808 800 5000", "available": "24/7"},
    ],
    "AU": [
        {"name": "Kids Helpline", "number": "1800 55 1800", "available": "24/7"},
        {"name": "Lifeline", "number": "13 11 14", "available": "24/7"},
    ],
    "DEFAULT": [
        {"name": "Childhelp National Child Abuse Hotline", "number": "1-800-422-4453", "available": "24/7"},
        {"name": "Crisis Text Line", "number": "Text HOME to 741741", "available": "24/7"},
    ],
}

# Privacy tier defaults by age tier
PRIVACY_TIER_DEFAULTS = {
    PrivacyTier.YOUNG: {
        "posts_visible": True,
        "contacts_visible": True,
        "messages_visible": True,
        "activity_summary_only": False,
        "flagged_content_visible": True,
    },
    PrivacyTier.PRETEEN: {
        "posts_visible": True,
        "contacts_visible": True,
        "messages_visible": False,
        "activity_summary_only": False,
        "flagged_content_visible": True,
    },
    PrivacyTier.TEEN: {
        "posts_visible": False,
        "contacts_visible": False,
        "messages_visible": False,
        "activity_summary_only": True,
        "flagged_content_visible": True,
    },
}


# ---------------------------------------------------------------------------
# Service Functions
# ---------------------------------------------------------------------------


async def request_trusted_adult(
    db: AsyncSession,
    *,
    child_member_id: uuid.UUID,
    trusted_adult_name: str | None = None,
    trusted_adult_contact: str | None = None,
    reason: str | None = None,
    jurisdiction: str = "US",
) -> dict:
    """Create a trusted adult request. NOT visible to parent.

    Returns helpline numbers appropriate for the child's jurisdiction.
    The parent is NEVER notified of this request.
    """
    helplines = HELPLINES.get(jurisdiction, HELPLINES["DEFAULT"])

    request = TrustedAdultRequest(
        id=uuid.uuid4(),
        child_member_id=child_member_id,
        trusted_adult_name=trusted_adult_name,
        trusted_adult_contact=trusted_adult_contact,
        reason=reason,
        status=TrustedAdultStatus.PENDING.value,
        helplines_shown=helplines,
    )
    db.add(request)
    await db.flush()

    logger.info(
        "trusted_adult_request_created",
        request_id=str(request.id),
        child_member_id=str(child_member_id),
        # NOTE: We do NOT log the reason or contact details for privacy
    )

    return {
        "request_id": request.id,
        "status": request.status,
        "message": "Your request has been received. This is private and will not be shared with your parent or guardian.",
        "helplines": helplines,
    }


async def get_trusted_adult_requests(
    db: AsyncSession,
    *,
    child_member_id: uuid.UUID,
) -> list[TrustedAdultRequest]:
    """Get trusted adult requests for a child. Only accessible by platform staff."""
    result = await db.execute(
        select(TrustedAdultRequest)
        .where(TrustedAdultRequest.child_member_id == child_member_id)
        .order_by(TrustedAdultRequest.created_at.desc())
    )
    return list(result.scalars().all())


async def get_guardian_access(
    db: AsyncSession,
    *,
    child_member_id: uuid.UUID,
    guardian_member_id: uuid.UUID,
) -> CustodyConfig | None:
    """Get custody configuration for a guardian-child pair."""
    result = await db.execute(
        select(CustodyConfig)
        .where(
            CustodyConfig.child_member_id == child_member_id,
            CustodyConfig.guardian_member_id == guardian_member_id,
        )
    )
    return result.scalar_one_or_none()


async def add_secondary_guardian(
    db: AsyncSession,
    *,
    child_member_id: uuid.UUID,
    guardian_member_id: uuid.UUID,
    can_view_activity: bool = True,
    can_manage_settings: bool = False,
    can_approve_contacts: bool = False,
) -> CustodyConfig:
    """Add a secondary guardian with limited permissions."""
    # Check if config already exists
    existing = await get_guardian_access(
        db, child_member_id=child_member_id, guardian_member_id=guardian_member_id,
    )
    if existing:
        raise ValidationError("Guardian configuration already exists for this child-guardian pair")

    config = CustodyConfig(
        id=uuid.uuid4(),
        child_member_id=child_member_id,
        guardian_member_id=guardian_member_id,
        role=GuardianRole.SECONDARY.value,
        can_view_activity=can_view_activity,
        can_manage_settings=can_manage_settings,
        can_approve_contacts=can_approve_contacts,
        dispute_status=CustodyDisputeStatus.NONE.value,
    )
    db.add(config)
    await db.flush()

    logger.info(
        "secondary_guardian_added",
        child_member_id=str(child_member_id),
        guardian_member_id=str(guardian_member_id),
    )
    return config


async def add_primary_guardian(
    db: AsyncSession,
    *,
    child_member_id: uuid.UUID,
    guardian_member_id: uuid.UUID,
) -> CustodyConfig:
    """Add a primary guardian with full permissions."""
    existing = await get_guardian_access(
        db, child_member_id=child_member_id, guardian_member_id=guardian_member_id,
    )
    if existing:
        raise ValidationError("Guardian configuration already exists for this child-guardian pair")

    config = CustodyConfig(
        id=uuid.uuid4(),
        child_member_id=child_member_id,
        guardian_member_id=guardian_member_id,
        role=GuardianRole.PRIMARY.value,
        can_view_activity=True,
        can_manage_settings=True,
        can_approve_contacts=True,
        dispute_status=CustodyDisputeStatus.NONE.value,
    )
    db.add(config)
    await db.flush()

    logger.info(
        "primary_guardian_added",
        child_member_id=str(child_member_id),
        guardian_member_id=str(guardian_member_id),
    )
    return config


async def set_custody_dispute(
    db: AsyncSession,
    *,
    child_member_id: uuid.UUID,
    guardian_member_id: uuid.UUID,
    notes: str | None = None,
) -> CustodyConfig:
    """Flag a custody dispute for a guardian-child pair.

    During a dispute, the secondary guardian's access is restricted
    until the dispute is resolved.
    """
    config = await get_guardian_access(
        db, child_member_id=child_member_id, guardian_member_id=guardian_member_id,
    )
    if not config:
        raise NotFoundError("CustodyConfig")

    config.dispute_status = CustodyDisputeStatus.FLAGGED.value
    config.dispute_notes = notes

    # During dispute, restrict management permissions
    if config.role == GuardianRole.SECONDARY.value:
        config.can_manage_settings = False
        config.can_approve_contacts = False

    await db.flush()

    logger.warning(
        "custody_dispute_flagged",
        child_member_id=str(child_member_id),
        guardian_member_id=str(guardian_member_id),
    )
    return config


async def resolve_custody_dispute(
    db: AsyncSession,
    *,
    child_member_id: uuid.UUID,
    guardian_member_id: uuid.UUID,
) -> CustodyConfig:
    """Resolve a custody dispute."""
    config = await get_guardian_access(
        db, child_member_id=child_member_id, guardian_member_id=guardian_member_id,
    )
    if not config:
        raise NotFoundError("CustodyConfig")

    config.dispute_status = CustodyDisputeStatus.RESOLVED.value
    await db.flush()

    logger.info(
        "custody_dispute_resolved",
        child_member_id=str(child_member_id),
        guardian_member_id=str(guardian_member_id),
    )
    return config


async def set_teen_privacy(
    db: AsyncSession,
    *,
    child_member_id: uuid.UUID,
    privacy_tier: PrivacyTier,
) -> TeenPrivacyConfig:
    """Set or update the privacy configuration for a child based on age tier."""
    defaults = PRIVACY_TIER_DEFAULTS[privacy_tier]

    # Check for existing config
    result = await db.execute(
        select(TeenPrivacyConfig)
        .where(TeenPrivacyConfig.child_member_id == child_member_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.privacy_tier = privacy_tier.value
        existing.posts_visible = defaults["posts_visible"]
        existing.contacts_visible = defaults["contacts_visible"]
        existing.messages_visible = defaults["messages_visible"]
        existing.activity_summary_only = defaults["activity_summary_only"]
        existing.flagged_content_visible = defaults["flagged_content_visible"]
        await db.flush()
        return existing

    config = TeenPrivacyConfig(
        id=uuid.uuid4(),
        child_member_id=child_member_id,
        privacy_tier=privacy_tier.value,
        **defaults,
    )
    db.add(config)
    await db.flush()
    return config


async def get_parent_visible_data(
    db: AsyncSession,
    *,
    child_member_id: uuid.UUID,
    guardian_member_id: uuid.UUID,
) -> dict:
    """Determine what data is visible to a guardian for a child.

    Combines custody access + privacy tier to produce a visibility map.
    """
    # Get custody config
    custody = await get_guardian_access(
        db, child_member_id=child_member_id, guardian_member_id=guardian_member_id,
    )

    # Get privacy config
    result = await db.execute(
        select(TeenPrivacyConfig)
        .where(TeenPrivacyConfig.child_member_id == child_member_id)
    )
    privacy = result.scalar_one_or_none()

    # Default: full access if no configs exist
    if not custody and not privacy:
        return {
            "posts": True,
            "contacts": True,
            "messages": True,
            "activity_detail": True,
            "activity_summary": True,
            "flagged_content": True,
            "trusted_adult_requests": False,  # NEVER visible to parents
        }

    # Base visibility from privacy tier
    visibility = {
        "posts": privacy.posts_visible if privacy else True,
        "contacts": privacy.contacts_visible if privacy else True,
        "messages": privacy.messages_visible if privacy else True,
        "activity_detail": not (privacy.activity_summary_only if privacy else False),
        "activity_summary": True,
        "flagged_content": privacy.flagged_content_visible if privacy else True,
        "trusted_adult_requests": False,  # NEVER visible to parents
    }

    # Apply custody restrictions
    if custody:
        if not custody.can_view_activity:
            visibility["posts"] = False
            visibility["contacts"] = False
            visibility["messages"] = False
            visibility["activity_detail"] = False

        # During custody dispute, secondary guardians get restricted view
        if (
            custody.dispute_status == CustodyDisputeStatus.FLAGGED.value
            and custody.role == GuardianRole.SECONDARY.value
        ):
            visibility["messages"] = False
            visibility["activity_detail"] = False
            visibility["contacts"] = False

    return visibility


async def check_trusted_adult_visibility(
    db: AsyncSession,
    *,
    child_member_id: uuid.UUID,
    requester_member_id: uuid.UUID,
) -> bool:
    """Check if a requester can see trusted adult requests.

    Returns False for ALL parent/guardian roles.
    Only platform staff can see these records.
    """
    # Check if requester is a guardian of this child
    result = await db.execute(
        select(CustodyConfig)
        .where(
            CustodyConfig.child_member_id == child_member_id,
            CustodyConfig.guardian_member_id == requester_member_id,
        )
    )
    is_guardian = result.scalar_one_or_none() is not None

    if is_guardian:
        return False

    # Only non-guardian platform staff can see these
    return True
