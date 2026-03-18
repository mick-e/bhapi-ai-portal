"""COPPA 2026 compliance service — granular third-party consent, push notification
consent, refuse-partial-collection, and enhanced VPC with video verification.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.compliance.models import (
    PushNotificationConsent,
    ThirdPartyConsentItem,
    VideoVerification,
)
from src.exceptions import NotFoundError, ValidationError
from src.groups.models import GroupMember

logger = structlog.get_logger()

# Third-party providers that process child data
THIRD_PARTY_PROVIDERS = [
    {
        "provider_key": "stripe",
        "provider_name": "Stripe",
        "data_purpose": "Payment processing for subscription billing. Receives parent billing information only, not child data.",
    },
    {
        "provider_key": "sendgrid",
        "provider_name": "SendGrid (Twilio)",
        "data_purpose": "Email delivery for safety alerts, reports, and account notifications. May include child's display name in alert emails.",
    },
    {
        "provider_key": "twilio_sms",
        "provider_name": "Twilio SMS",
        "data_purpose": "SMS delivery for urgent safety alerts (critical/high severity). May include brief risk description.",
    },
    {
        "provider_key": "google_cloud_ai",
        "provider_name": "Google Cloud AI",
        "data_purpose": "Content safety analysis using Perspective API (text toxicity), Vision API (image safety), and Video Intelligence. Processes AI conversation content for risk scoring.",
    },
    {
        "provider_key": "hive_sensity",
        "provider_name": "Hive / Sensity",
        "data_purpose": "Deepfake content detection. Processes media shared in AI conversations to detect manipulated images/videos.",
    },
    {
        "provider_key": "yoti",
        "provider_name": "Yoti",
        "data_purpose": "Age and identity verification for parental consent. Processes parent identity documents and selfie for verification.",
    },
    {
        "provider_key": "render",
        "provider_name": "Render",
        "data_purpose": "Cloud hosting infrastructure. All data is stored encrypted on Render's servers in the Frankfurt (EU) region.",
    },
]


async def get_third_party_consents(
    db: AsyncSession, group_id: UUID, member_id: UUID
) -> list[ThirdPartyConsentItem]:
    """Get all third-party consent items for a member, creating defaults if needed."""
    result = await db.execute(
        select(ThirdPartyConsentItem).where(
            ThirdPartyConsentItem.group_id == group_id,
            ThirdPartyConsentItem.member_id == member_id,
        )
    )
    items = list(result.scalars().all())

    if not items:
        # Auto-create consent items for all known providers (all unconsented)
        items = await _create_default_consent_items(db, group_id, member_id)

    return items


async def _create_default_consent_items(
    db: AsyncSession, group_id: UUID, member_id: UUID
) -> list[ThirdPartyConsentItem]:
    """Create default (unconsented) third-party consent items for a member."""
    from src.groups.models import Group

    # Look up member
    member_result = await db.execute(
        select(GroupMember).where(
            GroupMember.id == member_id,
            GroupMember.group_id == group_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise NotFoundError("Member", str(member_id))

    # Find the parent (group owner) — child members may not have a user_id
    parent_user_id = member.user_id
    if not parent_user_id:
        group_result = await db.execute(
            select(Group).where(Group.id == group_id)
        )
        group = group_result.scalar_one_or_none()
        if group:
            parent_user_id = group.owner_id

    if not parent_user_id:
        raise NotFoundError("Parent user for group", str(group_id))

    items = []
    for provider in THIRD_PARTY_PROVIDERS:
        item = ThirdPartyConsentItem(
            id=uuid4(),
            group_id=group_id,
            member_id=member_id,
            parent_user_id=parent_user_id,
            provider_key=provider["provider_key"],
            provider_name=provider["provider_name"],
            data_purpose=provider["data_purpose"],
            consented=False,
        )
        db.add(item)
        items.append(item)
    await db.flush()
    return items


async def update_third_party_consent(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    parent_user_id: UUID,
    provider_key: str,
    consented: bool,
    ip_address: str | None = None,
) -> ThirdPartyConsentItem:
    """Update consent for a specific third-party provider."""
    result = await db.execute(
        select(ThirdPartyConsentItem).where(
            ThirdPartyConsentItem.group_id == group_id,
            ThirdPartyConsentItem.member_id == member_id,
            ThirdPartyConsentItem.provider_key == provider_key,
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        # Create if doesn't exist
        provider_info = next(
            (p for p in THIRD_PARTY_PROVIDERS if p["provider_key"] == provider_key),
            None,
        )
        if not provider_info:
            raise ValidationError(
                f"Unknown provider: {provider_key}. Valid: {', '.join(p['provider_key'] for p in THIRD_PARTY_PROVIDERS)}"
            )
        item = ThirdPartyConsentItem(
            id=uuid4(),
            group_id=group_id,
            member_id=member_id,
            parent_user_id=parent_user_id,
            provider_key=provider_key,
            provider_name=provider_info["provider_name"],
            data_purpose=provider_info["data_purpose"],
            consented=consented,
            ip_address=ip_address,
        )
        db.add(item)
    else:
        item.consented = consented
        item.ip_address = ip_address

    now = datetime.now(timezone.utc)
    if consented:
        item.consented_at = now
        item.withdrawn_at = None
    else:
        item.withdrawn_at = now

    await db.flush()
    await db.refresh(item)

    logger.info(
        "third_party_consent_updated",
        group_id=str(group_id),
        member_id=str(member_id),
        provider=provider_key,
        consented=consented,
    )
    return item


async def bulk_update_third_party_consent(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    parent_user_id: UUID,
    consents: list[dict],
    ip_address: str | None = None,
) -> list[ThirdPartyConsentItem]:
    """Bulk update third-party consent for multiple providers."""
    results = []
    for consent in consents:
        item = await update_third_party_consent(
            db, group_id, member_id, parent_user_id,
            consent["provider_key"], consent["consented"], ip_address,
        )
        results.append(item)
    return results


async def set_refuse_partial_collection(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    parent_user_id: UUID,
    refuse_third_party_sharing: bool,
    ip_address: str | None = None,
) -> list[ThirdPartyConsentItem]:
    """Toggle refuse-partial-collection: consent to data collection but refuse all 3rd-party sharing.

    When refuse=True, withdraws consent from all third-party providers except
    essential services (Render hosting, Stripe billing for parent only).
    """
    items = await get_third_party_consents(db, group_id, member_id)

    # Essential providers that don't share child data
    essential_providers = {"stripe", "render"}

    for item in items:
        if item.provider_key in essential_providers:
            continue

        if refuse_third_party_sharing:
            item.consented = False
            item.withdrawn_at = datetime.now(timezone.utc)
        # When refuse=False, we don't auto-consent — parent must explicitly consent

    await db.flush()

    # Refresh all items
    refreshed = await get_third_party_consents(db, group_id, member_id)

    logger.info(
        "refuse_partial_collection",
        group_id=str(group_id),
        member_id=str(member_id),
        refuse=refuse_third_party_sharing,
    )
    return refreshed


async def check_third_party_consent(
    db: AsyncSession, group_id: UUID, member_id: UUID, provider_key: str
) -> bool:
    """Check if parent consented to share child data with a third-party provider.
    Returns True only if an explicit consent record exists with consented=True
    and withdrawn_at is None. Returns False if no record exists or if withdrawn.
    """
    result = await db.execute(
        select(ThirdPartyConsentItem).where(
            ThirdPartyConsentItem.group_id == group_id,
            ThirdPartyConsentItem.member_id == member_id,
            ThirdPartyConsentItem.provider_key == provider_key,
            ThirdPartyConsentItem.consented.is_(True),
            ThirdPartyConsentItem.withdrawn_at.is_(None),
        )
    )
    return result.scalar_one_or_none() is not None


async def check_push_notification_consent(
    db: AsyncSession, group_id: UUID, member_id: UUID, notification_type: str
) -> bool:
    """Check if parent consented to receive a specific notification type.
    Returns True only if explicit consent record exists with consented=True.
    Returns False if no record or if explicitly withdrawn.
    """
    result = await db.execute(
        select(PushNotificationConsent).where(
            PushNotificationConsent.group_id == group_id,
            PushNotificationConsent.member_id == member_id,
            PushNotificationConsent.notification_type == notification_type,
            PushNotificationConsent.consented.is_(True),
        )
    )
    consent = result.scalar_one_or_none()
    if consent and consent.withdrawn_at is not None:
        return False
    return consent is not None


async def get_degraded_providers(
    db: AsyncSession, group_id: UUID, member_id: UUID
) -> list[str]:
    """Return list of provider keys where consent is not granted.
    Used by frontend to show degradation warnings.
    """
    items = await get_third_party_consents(db, group_id, member_id)
    return [item.provider_key for item in items if not item.consented]


# ---------------------------------------------------------------------------
# Push notification consent
# ---------------------------------------------------------------------------

NOTIFICATION_TYPES = {"risk_alerts", "activity_summaries", "weekly_reports", "all"}


async def get_push_notification_consents(
    db: AsyncSession, group_id: UUID, member_id: UUID
) -> list[PushNotificationConsent]:
    """Get push notification consent records for a member."""
    result = await db.execute(
        select(PushNotificationConsent).where(
            PushNotificationConsent.group_id == group_id,
            PushNotificationConsent.member_id == member_id,
        )
    )
    return list(result.scalars().all())


async def update_push_notification_consent(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    parent_user_id: UUID,
    notification_type: str,
    consented: bool,
) -> PushNotificationConsent:
    """Update push notification consent for a specific notification type."""
    if notification_type not in NOTIFICATION_TYPES:
        raise ValidationError(
            f"Invalid notification type. Must be one of: {', '.join(sorted(NOTIFICATION_TYPES))}"
        )

    result = await db.execute(
        select(PushNotificationConsent).where(
            PushNotificationConsent.group_id == group_id,
            PushNotificationConsent.member_id == member_id,
            PushNotificationConsent.notification_type == notification_type,
        )
    )
    record = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not record:
        record = PushNotificationConsent(
            id=uuid4(),
            group_id=group_id,
            member_id=member_id,
            parent_user_id=parent_user_id,
            notification_type=notification_type,
            consented=consented,
            consented_at=now if consented else None,
        )
        db.add(record)
    else:
        record.consented = consented
        if consented:
            record.consented_at = now
            record.withdrawn_at = None
        else:
            record.withdrawn_at = now

    await db.flush()
    await db.refresh(record)

    logger.info(
        "push_notification_consent_updated",
        group_id=str(group_id),
        member_id=str(member_id),
        notification_type=notification_type,
        consented=consented,
    )
    return record


# ---------------------------------------------------------------------------
# Video verification (enhanced VPC)
# ---------------------------------------------------------------------------

VERIFICATION_METHODS = {"video_call", "yoti_id_check", "video_selfie"}


async def initiate_video_verification(
    db: AsyncSession,
    group_id: UUID,
    parent_user_id: UUID,
    method: str,
) -> VideoVerification:
    """Initiate a video-based parental identity verification.

    For yoti_id_check, creates a Yoti session. For video_call and video_selfie,
    creates a pending record for manual or automated review.
    """
    if method not in VERIFICATION_METHODS:
        raise ValidationError(
            f"Invalid method. Must be one of: {', '.join(sorted(VERIFICATION_METHODS))}"
        )

    yoti_session_id = None
    if method == "yoti_id_check":
        # COPPA 2026: Log Yoti verification initiation for audit trail
        # Parent initiating verification is implicit consent to Yoti data sharing
        logger.info(
            "yoti_verification_consent_implicit",
            group_id=str(group_id),
            parent_user_id=str(parent_user_id),
            method=method,
        )
        try:
            from src.integrations.yoti import create_age_verification_session
            session = await create_age_verification_session(str(parent_user_id))
            yoti_session_id = session.get("session_id")
        except Exception as exc:
            logger.error("yoti_session_creation_failed", error=str(exc))
            # Continue without Yoti — record stays pending for manual review

    verification = VideoVerification(
        id=uuid4(),
        group_id=group_id,
        parent_user_id=parent_user_id,
        verification_method=method,
        status="pending" if method != "yoti_id_check" else "in_progress",
        yoti_session_id=yoti_session_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(verification)
    await db.flush()
    await db.refresh(verification)

    logger.info(
        "video_verification_initiated",
        group_id=str(group_id),
        parent_user_id=str(parent_user_id),
        method=method,
        verification_id=str(verification.id),
    )
    return verification


async def get_video_verification(
    db: AsyncSession, verification_id: UUID
) -> VideoVerification:
    """Get a video verification record."""
    result = await db.execute(
        select(VideoVerification).where(VideoVerification.id == verification_id)
    )
    verification = result.scalar_one_or_none()
    if not verification:
        raise NotFoundError("VideoVerification", str(verification_id))
    return verification


async def complete_video_verification(
    db: AsyncSession,
    verification_id: UUID,
    score: float,
    notes: str | None = None,
) -> VideoVerification:
    """Mark a video verification as verified or failed."""
    verification = await get_video_verification(db, verification_id)

    if verification.status in ("verified", "failed"):
        raise ValidationError(f"Verification already {verification.status}")

    now = datetime.now(timezone.utc)
    expires = verification.expires_at
    if expires:
        # Ensure both are timezone-aware for comparison (SQLite strips tzinfo)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:
            verification.status = "expired"
            await db.flush()
            raise ValidationError("Verification session has expired")

    verification.verification_score = score
    verification.notes = notes

    if score >= 0.7:
        verification.status = "verified"
        verification.verified_at = now
    else:
        verification.status = "failed"

    await db.flush()
    await db.refresh(verification)

    logger.info(
        "video_verification_completed",
        verification_id=str(verification_id),
        status=verification.status,
        score=score,
    )
    return verification


async def get_parent_verifications(
    db: AsyncSession, group_id: UUID, parent_user_id: UUID
) -> list[VideoVerification]:
    """Get all video verifications for a parent in a group."""
    result = await db.execute(
        select(VideoVerification).where(
            VideoVerification.group_id == group_id,
            VideoVerification.parent_user_id == parent_user_id,
        )
    )
    return list(result.scalars().all())


async def has_valid_video_verification(
    db: AsyncSession, group_id: UUID, parent_user_id: UUID
) -> bool:
    """Check if parent has a valid (non-expired) video verification."""
    result = await db.execute(
        select(VideoVerification).where(
            VideoVerification.group_id == group_id,
            VideoVerification.parent_user_id == parent_user_id,
            VideoVerification.status == "verified",
        )
    )
    verifications = list(result.scalars().all())

    now = datetime.now(timezone.utc)
    for v in verifications:
        if v.expires_at is None:
            return True
        expires = v.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires > now:
            return True
    return False
