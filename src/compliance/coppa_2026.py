"""COPPA 2026 compliance service — granular third-party consent, push notification
consent, refuse-partial-collection, and enhanced VPC with video verification.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.compliance.models import (
    PushNotificationConsent,
    RetentionPolicy,
    ThirdPartyConsentItem,
    VideoVerification,
)
from src.exceptions import NotFoundError, ValidationError
from src.groups import GroupMember

logger = structlog.get_logger()

# Third-party providers that process child data
THIRD_PARTY_PROVIDERS = [
    {
        "provider_key": "stripe",
        "provider_name": "Stripe",
        "data_purpose": (
            "Payment processing for subscription billing."
            " Receives parent billing information only, not child data."
        ),
    },
    {
        "provider_key": "sendgrid",
        "provider_name": "SendGrid (Twilio)",
        "data_purpose": (
            "Email delivery for safety alerts, reports, and account notifications."
            " May include child's display name in alert emails."
        ),
    },
    {
        "provider_key": "twilio_sms",
        "provider_name": "Twilio SMS",
        "data_purpose": (
            "SMS delivery for urgent safety alerts (critical/high severity)."
            " May include brief risk description."
        ),
    },
    {
        "provider_key": "google_cloud_ai",
        "provider_name": "Google Cloud AI",
        "data_purpose": (
            "Content safety analysis using Perspective API (text toxicity),"
            " Vision API (image safety), and Video Intelligence."
            " Processes AI conversation content for risk scoring."
        ),
    },
    {
        "provider_key": "hive_sensity",
        "provider_name": "Hive / Sensity",
        "data_purpose": (
            "Deepfake content detection. Processes media shared in AI"
            " conversations to detect manipulated images/videos."
        ),
    },
    {
        "provider_key": "yoti",
        "provider_name": "Yoti",
        "data_purpose": (
            "Age and identity verification for parental consent."
            " Processes parent identity documents and selfie for verification."
        ),
    },
    {
        "provider_key": "render",
        "provider_name": "Render",
        "data_purpose": (
            "Cloud hosting infrastructure. All data is stored encrypted"
            " on Render's servers in the Frankfurt (EU) region."
        ),
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
                f"Unknown provider: {provider_key}. Valid: "
                f"{', '.join(p['provider_key'] for p in THIRD_PARTY_PROVIDERS)}"
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


async def generate_safe_harbor_certificate(
    db: AsyncSession, group_id: UUID
) -> dict:
    """Generate safe harbor compliance certificate data.

    Shows FTC-approved verification methods used and verification history.
    """
    from src.groups.models import Group

    # Get group info
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise NotFoundError("Group", str(group_id))

    # Get all video verifications for this group
    verifications = await db.execute(
        select(VideoVerification).where(
            VideoVerification.group_id == group_id,
        )
    )
    verification_list = list(verifications.scalars().all())

    verified_count = sum(1 for v in verification_list if v.status == "verified")
    methods_used = list(set(v.verification_method for v in verification_list))

    return {
        "group_name": group.name,
        "group_id": str(group_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "compliance_status": "compliant" if verified_count > 0 else "pending",
        "verification_methods_available": ["video_selfie", "yoti_id_check", "video_call"],
        "verification_methods_used": methods_used,
        "total_verifications": len(verification_list),
        "successful_verifications": verified_count,
        "verification_history": [
            {
                "method": v.verification_method,
                "status": v.status,
                "initiated_at": v.created_at.isoformat() if v.created_at else None,
                "verified_at": v.verified_at.isoformat() if v.verified_at else None,
                "score": v.verification_score,
            }
            for v in verification_list
        ],
        "ftc_methods_description": (
            "This organization uses FTC-approved verifiable parental consent methods "
            "including video-based identity verification and government ID checks "
            "per 16 CFR \u00a7 312.5(b)."
        ),
    }


async def generate_safe_harbor_certificate_pdf(
    db: AsyncSession, group_id: UUID
) -> bytes:
    """Generate a PDF safe harbor compliance certificate.

    Uses ReportLab to create a certificate-style document.
    """
    import io

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    cert_data = await generate_safe_harbor_certificate(db, group_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title="COPPA Safe Harbor Compliance Certificate",
    )
    styles = getSampleStyleSheet()

    # Custom styles with unique names to avoid ReportLab conflicts
    title_style = ParagraphStyle(
        "SafeHarborTitle",
        parent=styles["Heading1"],
        fontSize=20,
        spaceAfter=16,
        alignment=1,  # center
    )
    heading_style = ParagraphStyle(
        "SafeHarborHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "SafeHarborBody",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=6,
    )
    footer_style = ParagraphStyle(
        "SafeHarborFooter",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
        alignment=1,
    )

    elements: list = []

    # Title
    elements.append(Paragraph("COPPA Safe Harbor Compliance Certificate", title_style))
    elements.append(Spacer(1, 0.3 * inch))

    # Organization info
    elements.append(Paragraph("Organization Details", heading_style))
    elements.append(Paragraph(f"Organization: {cert_data['group_name']}", body_style))
    elements.append(Paragraph(f"Group ID: {cert_data['group_id']}", body_style))
    elements.append(Paragraph(f"Generated: {cert_data['generated_at']}", body_style))
    elements.append(Paragraph(
        f"Compliance Status: {cert_data['compliance_status'].title()}",
        body_style,
    ))
    elements.append(Spacer(1, 0.3 * inch))

    # Verification methods
    elements.append(Paragraph("FTC-Approved Verification Methods", heading_style))
    methods_used = cert_data["verification_methods_used"]
    if methods_used:
        elements.append(Paragraph(
            f"Methods used: {', '.join(m.replace('_', ' ').title() for m in methods_used)}",
            body_style,
        ))
    else:
        elements.append(Paragraph("No verification methods used yet.", body_style))
    elements.append(Paragraph(
        f"Total verifications: {cert_data['total_verifications']}",
        body_style,
    ))
    elements.append(Paragraph(
        f"Successful verifications: {cert_data['successful_verifications']}",
        body_style,
    ))
    elements.append(Spacer(1, 0.3 * inch))

    # Verification history table
    history = cert_data["verification_history"]
    if history:
        elements.append(Paragraph("Verification History", heading_style))
        table_data = [["Method", "Status", "Initiated", "Verified", "Score"]]
        for entry in history:
            table_data.append([
                entry["method"].replace("_", " ").title(),
                entry["status"].title(),
                entry["initiated_at"] or "N/A",
                entry["verified_at"] or "N/A",
                str(entry["score"]) if entry["score"] is not None else "N/A",
            ])
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a365d")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))

    # FTC citation
    elements.append(Paragraph("Regulatory Reference", heading_style))
    elements.append(Paragraph(cert_data["ftc_methods_description"], body_style))
    elements.append(Spacer(1, 0.5 * inch))

    # Footer disclaimer
    elements.append(Paragraph(
        "This document is generated for compliance evidence purposes.",
        footer_style,
    ))
    elements.append(Paragraph(
        "bhapi.ai \u2014 Family AI Governance Platform",
        footer_style,
    ))

    doc.build(elements)
    logger.info(
        "safe_harbor_certificate_pdf_generated",
        group_id=str(group_id),
    )
    return buffer.getvalue()


async def get_data_dashboard(
    db: AsyncSession, group_id: UUID, member_id: UUID
) -> dict:
    """Build a parental data collection dashboard for a child member.

    Aggregates capture events, risk events, alerts, third-party consent status,
    retention policies, and degraded providers into a single response for
    COPPA 2026 parental transparency requirements.
    """
    from src.alerts.models import Alert
    from src.capture.models import CaptureEvent
    from src.risk.models import RiskEvent

    # Verify member exists
    member_result = await db.execute(
        select(GroupMember).where(
            GroupMember.id == member_id,
            GroupMember.group_id == group_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise NotFoundError("Member", str(member_id))

    # Capture events count
    capture_count_result = await db.execute(
        select(sa_func.count()).select_from(CaptureEvent).where(
            CaptureEvent.group_id == group_id,
            CaptureEvent.member_id == member_id,
        )
    )
    capture_events_count = capture_count_result.scalar() or 0

    # Distinct platforms monitored
    platforms_result = await db.execute(
        select(CaptureEvent.platform).where(
            CaptureEvent.group_id == group_id,
            CaptureEvent.member_id == member_id,
        ).distinct()
    )
    platforms_monitored = [row[0] for row in platforms_result.all()]

    # Risk events count
    risk_count_result = await db.execute(
        select(sa_func.count()).select_from(RiskEvent).where(
            RiskEvent.group_id == group_id,
            RiskEvent.member_id == member_id,
        )
    )
    risk_events_count = risk_count_result.scalar() or 0

    # High severity risk events (high + critical)
    high_severity_result = await db.execute(
        select(sa_func.count()).select_from(RiskEvent).where(
            RiskEvent.group_id == group_id,
            RiskEvent.member_id == member_id,
            RiskEvent.severity.in_(["high", "critical"]),
        )
    )
    high_severity_count = high_severity_result.scalar() or 0

    # Alerts count
    alerts_count_result = await db.execute(
        select(sa_func.count()).select_from(Alert).where(
            Alert.group_id == group_id,
            Alert.member_id == member_id,
        )
    )
    alerts_sent_count = alerts_count_result.scalar() or 0

    # Third-party consent status
    consent_items = await get_third_party_consents(db, group_id, member_id)
    third_party_sharing = [
        {
            "provider": item.provider_name,
            "consented": item.consented,
            "last_updated": (
                (item.consented_at or item.withdrawn_at or item.created_at).isoformat()
                if (item.consented_at or item.withdrawn_at or item.created_at)
                else None
            ),
        }
        for item in consent_items
    ]

    # Retention policies for this group
    retention_result = await db.execute(
        select(RetentionPolicy).where(RetentionPolicy.group_id == group_id)
    )
    retention_rows = list(retention_result.scalars().all())
    now = datetime.now(timezone.utc)
    retention_policies = [
        {
            "data_type": rp.data_type,
            "retention_days": rp.retention_days,
            "auto_delete": rp.auto_delete,
            "estimated_deletion": (
                (now + timedelta(days=rp.retention_days)).isoformat()
                if rp.auto_delete
                else None
            ),
        }
        for rp in retention_rows
    ]

    # Degraded providers
    degraded = await get_degraded_providers(db, group_id, member_id)

    logger.info(
        "data_dashboard_generated",
        group_id=str(group_id),
        member_id=str(member_id),
        capture_count=capture_events_count,
        risk_count=risk_events_count,
    )

    return {
        "member_name": member.display_name,
        "data_summary": {
            "capture_events_count": capture_events_count,
            "platforms_monitored": platforms_monitored,
            "risk_events_count": risk_events_count,
            "high_severity_count": high_severity_count,
            "alerts_sent_count": alerts_sent_count,
        },
        "third_party_sharing": third_party_sharing,
        "retention_policies": retention_policies,
        "degraded_providers": degraded,
    }


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
