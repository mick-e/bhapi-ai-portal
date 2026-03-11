"""COPPA 2026 Compliance Dashboard — auto-assessment and evidence export."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.compliance.models import ConsentRecord
from src.exceptions import NotFoundError
from src.groups.models import Group, GroupMember

logger = structlog.get_logger()


@dataclass
class COPPAChecklistItem:
    """A single item in the COPPA compliance checklist."""

    id: str
    label: str
    description: str
    status: str  # complete, incomplete, warning, not_applicable
    evidence: str
    action_url: str
    regulation_ref: str


@dataclass
class COPPAComplianceReport:
    """Full COPPA compliance assessment for a group."""

    group_id: str
    group_name: str
    score: float  # 0-100
    status: str  # compliant, partial, non_compliant
    checklist: list[COPPAChecklistItem] = field(default_factory=list)
    assessed_at: str = ""
    last_review: str | None = None


# ---------------------------------------------------------------------------
# Checklist definitions
# ---------------------------------------------------------------------------

_CHECKLIST_DEFS = [
    {
        "id": "consent_all_members",
        "label": "Parental consent for all members",
        "description": "Verifiable parental consent must be obtained for every minor in the group before collecting personal information.",
        "regulation_ref": "16 CFR 312.5(a)",
        "action_url": "/members",
    },
    {
        "id": "ftc_approved_method",
        "label": "FTC-approved consent method",
        "description": "Consent must be obtained via an FTC-approved verification method such as signed form, video call, or credit card verification.",
        "regulation_ref": "16 CFR 312.5(b)",
        "action_url": "/compliance",
    },
    {
        "id": "pii_detection_enabled",
        "label": "PII detection enabled",
        "description": "Automated PII detection must be active to prevent inadvertent collection of children's personal information.",
        "regulation_ref": "16 CFR 312.3(e)",
        "action_url": "/settings",
    },
    {
        "id": "content_encryption",
        "label": "Content encryption at rest",
        "description": "All stored content excerpts and personal data must be encrypted at rest using industry-standard encryption.",
        "regulation_ref": "16 CFR 312.8",
        "action_url": "/settings",
    },
    {
        "id": "data_retention_policy",
        "label": "Data retention policy defined",
        "description": "A clear data retention and deletion policy must be established, with content excerpts subject to automatic TTL expiration.",
        "regulation_ref": "16 CFR 312.10",
        "action_url": "/settings",
    },
    {
        "id": "deletion_requests_72h",
        "label": "Deletion requests honored within 72 hours",
        "description": "Data deletion requests from parents must be processed and completed within 72 hours of submission.",
        "regulation_ref": "16 CFR 312.6(a)(2)",
        "action_url": "/compliance",
    },
    {
        "id": "privacy_policy_accessible",
        "label": "Privacy policy accessible",
        "description": "A clear, prominently placed privacy policy describing data practices for children must be publicly accessible.",
        "regulation_ref": "16 CFR 312.4",
        "action_url": "/legal/privacy",
    },
    {
        "id": "no_marketing_to_children",
        "label": "No marketing to children",
        "description": "No behavioural advertising, push notifications for marketing, or gamification techniques targeting children.",
        "regulation_ref": "16 CFR 312.7",
        "action_url": "/settings",
    },
    {
        "id": "third_party_audit",
        "label": "Third-party audit scheduled",
        "description": "An independent third-party audit of data practices should be conducted annually for Safe Harbor certification.",
        "regulation_ref": "16 CFR 312.11",
        "action_url": "/compliance/coppa",
    },
    {
        "id": "infosec_docs",
        "label": "Information security documentation",
        "description": "Written information security policies and procedures must be maintained and reviewed regularly.",
        "regulation_ref": "16 CFR 312.8",
        "action_url": "/compliance/coppa",
    },
    {
        "id": "biometric_handling",
        "label": "Biometric data handling",
        "description": "If biometric data (facial recognition, voice) is collected, explicit parental consent and secure handling are required.",
        "regulation_ref": "16 CFR 312.2 (2024 amendment)",
        "action_url": "/settings",
    },
    {
        "id": "annual_review",
        "label": "Annual compliance review completed",
        "description": "A comprehensive review of COPPA compliance must be conducted at least annually and documented.",
        "regulation_ref": "16 CFR 312.11(b)",
        "action_url": "/compliance/coppa",
    },
]

# Items that are always complete because the platform provides them
_ALWAYS_COMPLETE = {
    "content_encryption",
    "data_retention_policy",
    "deletion_requests_72h",
    "privacy_policy_accessible",
    "no_marketing_to_children",
}


async def assess_coppa_compliance(db: AsyncSession, group_id: UUID) -> COPPAComplianceReport:
    """Auto-assess 12 COPPA checklist items for a group."""
    # Get group
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise NotFoundError("Group", str(group_id))

    # Get members
    members_result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id)
    )
    members = list(members_result.scalars().all())

    # Get consent records
    consent_result = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.group_id == group_id,
            ConsentRecord.withdrawn_at.is_(None),
        )
    )
    consents = list(consent_result.scalars().all())
    consented_ids = {c.member_id for c in consents}

    # Check for FTC-approved methods in consent evidence
    import json
    ftc_verified_count = 0
    for c in consents:
        if c.evidence:
            try:
                data = json.loads(c.evidence)
                if data.get("verification_status") == "verified":
                    ftc_verified_count += 1
            except (json.JSONDecodeError, TypeError):
                pass

    # Determine group settings
    settings = group.settings or {}
    pii_enabled = settings.get("pii_detection", True)

    # Check for minors
    from src.groups.consent import requires_consent
    minors = [m for m in members if m.date_of_birth and requires_consent(m.date_of_birth, "us")]
    all_consented = len(minors) == 0 or all(m.id in consented_ids for m in minors)

    # Check for annual review in settings
    last_review = settings.get("coppa_last_review")
    review_current = False
    if last_review:
        try:
            review_date = datetime.fromisoformat(last_review)
            days_since = (datetime.now(timezone.utc) - review_date).days
            review_current = days_since <= 365
        except (ValueError, TypeError):
            pass

    # Build checklist items
    checklist: list[COPPAChecklistItem] = []
    for defn in _CHECKLIST_DEFS:
        item_id = defn["id"]
        status = "incomplete"
        evidence = ""

        if item_id in _ALWAYS_COMPLETE:
            status = "complete"
            evidence = "Platform provides this capability by default."

        elif item_id == "consent_all_members":
            if len(minors) == 0:
                status = "not_applicable"
                evidence = "No minors requiring consent in this group."
            elif all_consented:
                status = "complete"
                evidence = f"All {len(minors)} minor(s) have active consent records."
            else:
                missing = len(minors) - len([m for m in minors if m.id in consented_ids])
                status = "incomplete"
                evidence = f"{missing} minor(s) missing consent."

        elif item_id == "ftc_approved_method":
            if len(minors) == 0:
                status = "not_applicable"
                evidence = "No minors requiring consent in this group."
            elif ftc_verified_count >= len(minors):
                status = "complete"
                evidence = f"{ftc_verified_count} verified consent(s) using FTC-approved methods."
            elif ftc_verified_count > 0:
                status = "warning"
                evidence = f"Only {ftc_verified_count} of {len(minors)} consent(s) verified via FTC-approved method."
            else:
                status = "incomplete"
                evidence = "No consent verified via FTC-approved method."

        elif item_id == "pii_detection_enabled":
            if pii_enabled:
                status = "complete"
                evidence = "PII detection is enabled in group settings."
            else:
                status = "incomplete"
                evidence = "PII detection is disabled. Enable it in settings."

        elif item_id == "third_party_audit":
            status = "warning"
            evidence = "Schedule an independent third-party audit for Safe Harbor certification."

        elif item_id == "infosec_docs":
            status = "warning"
            evidence = "Ensure written information security policies are maintained and accessible."

        elif item_id == "biometric_handling":
            status = "not_applicable"
            evidence = "Bhapi does not collect biometric data from children."

        elif item_id == "annual_review":
            if review_current:
                status = "complete"
                evidence = f"Last review completed on {last_review}."
            else:
                status = "incomplete"
                evidence = "Annual compliance review is overdue or has never been completed."

        checklist.append(COPPAChecklistItem(
            id=item_id,
            label=defn["label"],
            description=defn["description"],
            status=status,
            evidence=evidence,
            action_url=defn["action_url"],
            regulation_ref=defn["regulation_ref"],
        ))

    # Calculate score
    total = len(checklist)
    applicable = [c for c in checklist if c.status != "not_applicable"]
    complete = len([c for c in applicable if c.status == "complete"])
    warnings = len([c for c in applicable if c.status == "warning"])
    applicable_count = len(applicable) if applicable else 1

    score = ((complete + warnings * 0.5) / applicable_count) * 100

    if score >= 90:
        overall_status = "compliant"
    elif score >= 50:
        overall_status = "partial"
    else:
        overall_status = "non_compliant"

    report = COPPAComplianceReport(
        group_id=str(group_id),
        group_name=group.name,
        score=round(score, 1),
        status=overall_status,
        checklist=checklist,
        assessed_at=datetime.now(timezone.utc).isoformat(),
        last_review=last_review,
    )

    logger.info(
        "coppa_dashboard_assessed",
        group_id=str(group_id),
        score=report.score,
        status=report.status,
    )

    return report


async def export_coppa_evidence(db: AsyncSession, group_id: UUID) -> bytes:
    """Generate a PDF evidence package for COPPA compliance.

    Uses ReportLab to create a structured PDF document.
    """
    report = await assess_coppa_compliance(db, group_id)

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

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="COPPA Compliance Evidence")
    styles = getSampleStyleSheet()

    # Custom styles with unique names to avoid conflicts
    title_style = ParagraphStyle(
        "COPPATitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "COPPAHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "COPPABody",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=6,
    )

    elements = []

    # Title
    elements.append(Paragraph("COPPA Compliance Evidence Package", title_style))
    elements.append(Paragraph(f"Group: {report.group_name}", body_style))
    elements.append(Paragraph(f"Generated: {report.assessed_at}", body_style))
    elements.append(Paragraph(
        f"Overall Score: {report.score}% ({report.status.replace('_', ' ').title()})",
        body_style,
    ))
    elements.append(Spacer(1, 0.3 * inch))

    # Checklist table
    elements.append(Paragraph("Compliance Checklist", heading_style))

    table_data = [["Item", "Status", "Evidence", "Regulation"]]
    for item in report.checklist:
        status_label = item.status.replace("_", " ").title()
        table_data.append([
            item.label,
            status_label,
            item.evidence[:80],
            item.regulation_ref,
        ])

    table = Table(table_data, colWidths=[2 * inch, 1 * inch, 2.5 * inch, 1.2 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FF6B35")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))

    # Footer
    elements.append(Paragraph(
        "This report is generated automatically by Bhapi AI Portal. "
        "It should be reviewed by a qualified compliance officer before "
        "submission to the FTC or any Safe Harbor program.",
        body_style,
    ))

    doc.build(elements)
    return buffer.getvalue()


async def mark_annual_review(db: AsyncSession, group_id: UUID) -> dict:
    """Mark the annual COPPA compliance review as complete."""
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise NotFoundError("Group", str(group_id))

    now = datetime.now(timezone.utc).isoformat()
    settings = dict(group.settings or {})
    settings["coppa_last_review"] = now
    group.settings = settings
    await db.flush()

    logger.info(
        "coppa_annual_review_marked",
        group_id=str(group_id),
        reviewed_at=now,
    )

    return {
        "group_id": str(group_id),
        "reviewed_at": now,
        "status": "complete",
    }


async def coppa_reminder_job(db: AsyncSession) -> dict:
    """Daily job to check for COPPA compliance gaps and overdue reviews."""
    from src.alerts.models import Alert
    from uuid import uuid4

    groups_result = await db.execute(select(Group))
    groups = list(groups_result.scalars().all())

    alerts_created = 0
    for group in groups:
        try:
            report = await assess_coppa_compliance(db, group.id)
            if report.status == "non_compliant" or report.score < 50:
                alert = Alert(
                    id=uuid4(),
                    group_id=group.id,
                    severity="medium",
                    title="COPPA Compliance Action Required",
                    body=f"Your COPPA compliance score is {report.score}%. Review the compliance dashboard for details.",
                )
                db.add(alert)
                alerts_created += 1

            # Check for overdue annual review
            settings = group.settings or {}
            last_review = settings.get("coppa_last_review")
            if last_review:
                try:
                    review_date = datetime.fromisoformat(last_review)
                    days_since = (datetime.now(timezone.utc) - review_date).days
                    if days_since > 335:  # Alert 30 days before due
                        alert = Alert(
                            id=uuid4(),
                            group_id=group.id,
                            severity="info",
                            title="COPPA Annual Review Due Soon",
                            body=f"Your annual COPPA review was last completed {days_since} days ago. Schedule a review before the 365-day deadline.",
                        )
                        db.add(alert)
                        alerts_created += 1
                except (ValueError, TypeError):
                    pass
        except Exception as exc:
            logger.warning(
                "coppa_reminder_error",
                group_id=str(group.id),
                error=str(exc),
            )

    await db.flush()
    logger.info("coppa_reminder_completed", alerts_created=alerts_created)
    return {"alerts_created": alerts_created}
