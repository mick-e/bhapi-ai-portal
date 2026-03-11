"""Family Safety Weekly Report — generation, PDF, and email delivery."""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError

logger = structlog.get_logger()


async def generate_family_weekly_report(
    db: AsyncSession,
    group_id: uuid.UUID,
) -> dict:
    """Generate comprehensive weekly report data.

    Sections:
    1. Family safety score (group avg + trend)
    2. Per-member: safety score, platforms used, risk counts, week comparison
    3. Highlights: best improvement, longest safe streak, literacy progress
    4. Action items: unresolved alerts, pending approvals
    """
    from src.alerts.models import Alert
    from src.capture.models import CaptureEvent
    from src.groups.models import Group, GroupMember
    from src.risk.models import RiskEvent

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    # 1. Fetch group
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise NotFoundError("Group", str(group_id))

    # 2. Fetch members
    members_result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id)
    )
    members = list(members_result.scalars().all())

    # 3. Compute per-member stats
    member_reports = []
    total_safety_score = 0

    for member in members:
        # This week's capture events
        this_week_events = await db.execute(
            select(func.count(CaptureEvent.id)).where(
                CaptureEvent.group_id == group_id,
                CaptureEvent.member_id == member.id,
                CaptureEvent.timestamp >= week_ago,
            )
        )
        this_week_count = this_week_events.scalar() or 0

        # Last week's capture events
        last_week_events = await db.execute(
            select(func.count(CaptureEvent.id)).where(
                CaptureEvent.group_id == group_id,
                CaptureEvent.member_id == member.id,
                CaptureEvent.timestamp >= two_weeks_ago,
                CaptureEvent.timestamp < week_ago,
            )
        )
        last_week_count = last_week_events.scalar() or 0

        # Risk events this week
        this_week_risks = await db.execute(
            select(func.count(RiskEvent.id)).where(
                RiskEvent.group_id == group_id,
                RiskEvent.member_id == member.id,
                RiskEvent.created_at >= week_ago,
            )
        )
        risk_count = this_week_risks.scalar() or 0

        # Simple safety score: 100 - (risk_count * 10), min 0
        safety_score = max(0, 100 - (risk_count * 10))
        total_safety_score += safety_score

        # Platforms used this week
        platform_result = await db.execute(
            select(CaptureEvent.platform).where(
                CaptureEvent.group_id == group_id,
                CaptureEvent.member_id == member.id,
                CaptureEvent.timestamp >= week_ago,
            ).distinct()
        )
        platforms = [r[0] for r in platform_result.all() if r[0]]

        member_reports.append({
            "member_id": str(member.id),
            "display_name": member.display_name,
            "role": member.role,
            "safety_score": safety_score,
            "platforms_used": platforms,
            "risk_count": risk_count,
            "events_this_week": this_week_count,
            "events_last_week": last_week_count,
            "week_change": this_week_count - last_week_count,
        })

    # 4. Group average safety score
    avg_safety = (
        total_safety_score / len(members) if members else 100
    )

    # 5. Unresolved alerts
    unresolved_result = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.group_id == group_id,
            Alert.status == "pending",
        )
    )
    unresolved_count = unresolved_result.scalar() or 0

    # 6. Highlights
    best_member = max(member_reports, key=lambda m: m["safety_score"]) if member_reports else None
    most_improved = None
    if member_reports:
        improvements = [
            m for m in member_reports
            if m["events_last_week"] > 0 and m["risk_count"] == 0
        ]
        if improvements:
            most_improved = improvements[0]

    report = {
        "group_id": str(group_id),
        "group_name": group.name,
        "generated_at": now.isoformat(),
        "period_start": week_ago.isoformat(),
        "period_end": now.isoformat(),
        "family_safety_score": round(avg_safety, 1),
        "member_count": len(members),
        "members": member_reports,
        "highlights": {
            "safest_member": best_member["display_name"] if best_member else None,
            "most_improved": most_improved["display_name"] if most_improved else None,
        },
        "action_items": {
            "unresolved_alerts": unresolved_count,
        },
    }

    logger.info(
        "family_weekly_report_generated",
        group_id=str(group_id),
        member_count=len(members),
    )
    return report


async def generate_family_weekly_pdf(
    db: AsyncSession,
    group_id: uuid.UUID,
) -> bytes:
    """Generate PDF using ReportLab. One page per member."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    report_data = await generate_family_weekly_report(db, group_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    # Custom styles with unique names
    title_style = ParagraphStyle(
        "FamilyReportTitle",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.HexColor("#FF6B35"),
    )
    heading_style = ParagraphStyle(
        "FamilyReportHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#0D9488"),
    )
    body_style = ParagraphStyle(
        "FamilyReportBody",
        parent=styles["Normal"],
        fontSize=10,
    )

    elements = []

    # Title
    elements.append(Paragraph("Bhapi Family Weekly Safety Report", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        f"Group: {report_data['group_name']} | "
        f"Period: {report_data['period_start'][:10]} to {report_data['period_end'][:10]}",
        body_style,
    ))
    elements.append(Spacer(1, 20))

    # Family Safety Score
    elements.append(Paragraph("Family Safety Score", heading_style))
    elements.append(Paragraph(
        f"Overall Score: {report_data['family_safety_score']} / 100",
        body_style,
    ))
    elements.append(Spacer(1, 15))

    # Member Summary Table
    elements.append(Paragraph("Member Summary", heading_style))
    elements.append(Spacer(1, 8))

    table_data = [["Member", "Safety Score", "Risks", "Events", "Change"]]
    for m in report_data["members"]:
        change = m["week_change"]
        change_str = f"+{change}" if change > 0 else str(change)
        table_data.append([
            m["display_name"],
            str(m["safety_score"]),
            str(m["risk_count"]),
            str(m["events_this_week"]),
            change_str,
        ])

    if len(table_data) > 1:
        table = Table(table_data, colWidths=[150, 80, 60, 60, 60])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D9488")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ]))
        elements.append(table)

    elements.append(Spacer(1, 15))

    # Highlights
    elements.append(Paragraph("Highlights", heading_style))
    highlights = report_data["highlights"]
    if highlights.get("safest_member"):
        elements.append(Paragraph(
            f"Safest member: {highlights['safest_member']}",
            body_style,
        ))
    if highlights.get("most_improved"):
        elements.append(Paragraph(
            f"Most improved: {highlights['most_improved']}",
            body_style,
        ))
    elements.append(Spacer(1, 15))

    # Action Items
    elements.append(Paragraph("Action Items", heading_style))
    elements.append(Paragraph(
        f"Unresolved alerts: {report_data['action_items']['unresolved_alerts']}",
        body_style,
    ))

    doc.build(elements)
    return buffer.getvalue()


async def send_family_weekly_report(
    db: AsyncSession,
    group_id: uuid.UUID,
) -> bool:
    """Generate PDF + email to all parents in group."""
    from src.groups.models import GroupMember

    # Generate PDF
    pdf_bytes = await generate_family_weekly_pdf(db, group_id)

    # Find parent members with user accounts
    members_result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.role == "parent",
            GroupMember.user_id.isnot(None),
        )
    )
    parents = list(members_result.scalars().all())

    if not parents:
        logger.info("no_parents_to_send_report", group_id=str(group_id))
        return False

    # Get parent emails
    from src.auth.models import User

    sent = False
    for parent in parents:
        user_result = await db.execute(
            select(User).where(User.id == parent.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user or not user.email:
            continue

        try:
            from src.email import send_email

            await send_email(
                to=user.email,
                subject="Your Weekly Family AI Safety Report — Bhapi",
                body=(
                    "Hi there,\n\n"
                    "Your weekly family AI safety report is attached.\n\n"
                    "Log in to bhapi.ai to view detailed activity and manage your family's AI usage.\n\n"
                    "— The Bhapi Team"
                ),
                attachment=pdf_bytes,
                attachment_name="bhapi-weekly-report.pdf",
            )
            sent = True
        except Exception as exc:
            logger.warning(
                "weekly_report_send_failed",
                user_id=str(user.id),
                error=str(exc),
            )

    logger.info("weekly_report_sent", group_id=str(group_id), sent=sent)
    return sent


# ---------------------------------------------------------------------------
# Background job
# ---------------------------------------------------------------------------


async def run_family_weekly_reports(db: AsyncSession) -> dict:
    """Send weekly family reports to all groups."""
    from src.groups.models import Group

    groups_result = await db.execute(
        select(Group).where(Group.type == "family")
    )
    groups = list(groups_result.scalars().all())

    sent_count = 0
    for group in groups:
        try:
            success = await send_family_weekly_report(db, group.id)
            if success:
                sent_count += 1
        except Exception as exc:
            logger.warning(
                "family_weekly_report_failed",
                group_id=str(group.id),
                error=str(exc),
            )

    return {"reports_sent": sent_count, "groups_processed": len(groups)}
