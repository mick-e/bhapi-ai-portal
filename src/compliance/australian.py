"""Australian Online Safety compliance — age verification, eSafety SLA, cyberbullying workflow.

Implements:
- Age verification enforcement for AU users (Online Safety Act 2021)
- eSafety Commissioner 24-hour SLA monitoring
- Structured cyberbullying case workflow (detect → document → notify parent → escalate)
"""

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.compliance.australian_models import (
    AgeVerificationRecord,
    CyberbullyingCase,
    ESafetyReport,
)
from src.encryption import encrypt_credential, decrypt_credential
from src.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ESAFETY_SLA_HOURS = 24
VALID_VERIFICATION_METHODS = {"yoti", "document", "self_declaration", "parent_verified"}
CYBERBULLYING_SEVERITIES = {"low", "medium", "high", "critical"}

CYBERBULLYING_WORKFLOW_STEPS = [
    {"step": "detect", "label": "Incident detected", "required": True},
    {"step": "document", "label": "Evidence documented", "required": True},
    {"step": "notify_parent", "label": "Parent/guardian notified", "required": True},
    {"step": "review", "label": "Case reviewed by moderator", "required": True},
    {"step": "action", "label": "Action taken", "required": True},
    {"step": "escalate", "label": "Escalated to eSafety (if needed)", "required": False},
    {"step": "resolve", "label": "Case resolved", "required": True},
]


# ---------------------------------------------------------------------------
# Age Verification Enforcement
# ---------------------------------------------------------------------------


async def check_au_age_requirement(
    db: AsyncSession,
    user_id: UUID,
    country_code: str,
) -> dict:
    """Check whether an AU user has verified their age for social access.

    Returns a dict with:
        - verified: bool
        - required: bool (True if AU user)
        - verification: dict | None (latest verification record)
    """
    required = country_code.upper() == "AU"

    if not required:
        return {
            "user_id": str(user_id),
            "country_code": country_code,
            "required": False,
            "verified": True,
            "verification": None,
        }

    # Look for a valid verification record
    result = await db.execute(
        select(AgeVerificationRecord)
        .where(AgeVerificationRecord.user_id == user_id)
        .where(AgeVerificationRecord.country_code == "AU")
        .where(AgeVerificationRecord.verified.is_(True))
        .order_by(AgeVerificationRecord.verified_at.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()

    if record:
        return {
            "user_id": str(user_id),
            "country_code": "AU",
            "required": True,
            "verified": True,
            "verification": {
                "id": str(record.id),
                "method": record.method,
                "verified_at": record.verified_at.isoformat() if record.verified_at else None,
            },
        }

    return {
        "user_id": str(user_id),
        "country_code": "AU",
        "required": True,
        "verified": False,
        "verification": None,
    }


async def create_age_verification(
    db: AsyncSession,
    user_id: UUID,
    country_code: str,
    method: str,
    verification_data: dict | None = None,
) -> AgeVerificationRecord:
    """Create an age verification record for an AU user."""
    if method not in VALID_VERIFICATION_METHODS:
        raise ValidationError(
            f"Invalid verification method: {method}. "
            f"Valid methods: {', '.join(sorted(VALID_VERIFICATION_METHODS))}"
        )

    encrypted_data = None
    if verification_data:
        encrypted_data = encrypt_credential(json.dumps(verification_data))

    now = datetime.now(timezone.utc)
    record = AgeVerificationRecord(
        id=uuid4(),
        user_id=user_id,
        country_code=country_code.upper(),
        method=method,
        verified=True,
        verified_at=now,
        verification_data=encrypted_data,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    logger.info(
        "au_age_verification_created",
        user_id=str(user_id),
        country_code=country_code,
        method=method,
    )
    return record


# ---------------------------------------------------------------------------
# eSafety SLA Monitoring
# ---------------------------------------------------------------------------


async def check_esafety_sla(
    db: AsyncSession,
    group_id: UUID | None = None,
) -> dict:
    """Check eSafety 24-hour SLA compliance.

    Returns summary of open reports, SLA breaches, and compliance status.
    """
    query = select(ESafetyReport)
    if group_id:
        query = query.where(ESafetyReport.group_id == group_id)

    result = await db.execute(query)
    reports = list(result.scalars().all())

    now = datetime.now(timezone.utc)
    total = len(reports)
    actioned = 0
    breached = 0
    pending = 0

    def _ensure_aware(dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware (SQLite returns naive)."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    for report in reports:
        if report.status == "actioned" and report.actioned_at:
            actioned += 1
            hours_taken = (
                _ensure_aware(report.actioned_at) - _ensure_aware(report.reported_at)
            ).total_seconds() / 3600
            if hours_taken > ESAFETY_SLA_HOURS:
                breached += 1
        elif report.status == "pending":
            pending += 1
            hours_waiting = (
                now - _ensure_aware(report.reported_at)
            ).total_seconds() / 3600
            if hours_waiting > ESAFETY_SLA_HOURS:
                breached += 1

    compliant = breached == 0
    compliance_rate = ((total - breached) / total * 100) if total > 0 else 100.0

    return {
        "sla_hours": ESAFETY_SLA_HOURS,
        "total_reports": total,
        "actioned": actioned,
        "pending": pending,
        "breached": breached,
        "compliant": compliant,
        "compliance_rate": round(compliance_rate, 1),
    }


async def create_esafety_report(
    db: AsyncSession,
    content_id: UUID,
    content_type: str,
    group_id: UUID | None = None,
) -> ESafetyReport:
    """Create an eSafety report for content that needs review."""
    now = datetime.now(timezone.utc)
    report = ESafetyReport(
        id=uuid4(),
        content_id=content_id,
        content_type=content_type,
        group_id=group_id,
        reported_at=now,
        sla_hours=ESAFETY_SLA_HOURS,
        status="pending",
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)

    logger.info(
        "esafety_report_created",
        report_id=str(report.id),
        content_id=str(content_id),
        content_type=content_type,
    )
    return report


async def action_esafety_report(
    db: AsyncSession,
    report_id: UUID,
    action_taken: str = "reviewed",
) -> ESafetyReport:
    """Mark an eSafety report as actioned."""
    result = await db.execute(
        select(ESafetyReport).where(ESafetyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise NotFoundError("eSafety report", str(report_id))

    now = datetime.now(timezone.utc)
    report.actioned_at = now
    report.status = "actioned"
    report.action_taken = action_taken
    await db.flush()
    await db.refresh(report)

    logger.info(
        "esafety_report_actioned",
        report_id=str(report_id),
        action_taken=action_taken,
    )
    return report


async def get_esafety_report(
    db: AsyncSession,
    group_id: UUID | None = None,
) -> dict:
    """Generate eSafety Commissioner compliance report."""
    sla_status = await check_esafety_sla(db, group_id)

    # Get recent reports
    query = (
        select(ESafetyReport)
        .order_by(ESafetyReport.reported_at.desc())
        .limit(50)
    )
    if group_id:
        query = query.where(ESafetyReport.group_id == group_id)

    result = await db.execute(query)
    reports = list(result.scalars().all())

    return {
        "report_type": "esafety_commissioner",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sla_compliance": sla_status,
        "recent_reports": [
            {
                "id": str(r.id),
                "content_id": str(r.content_id),
                "content_type": r.content_type,
                "reported_at": r.reported_at.isoformat(),
                "actioned_at": r.actioned_at.isoformat() if r.actioned_at else None,
                "status": r.status,
                "sla_hours": r.sla_hours,
            }
            for r in reports
        ],
    }


# ---------------------------------------------------------------------------
# Cyberbullying Case Workflow
# ---------------------------------------------------------------------------


async def create_cyberbullying_case(
    db: AsyncSession,
    reporter_id: UUID,
    target_id: UUID,
    evidence_ids: list[str],
    severity: str,
    description: str | None = None,
    group_id: UUID | None = None,
) -> CyberbullyingCase:
    """Create a structured cyberbullying case with workflow steps.

    Workflow: detect -> document -> notify_parent -> review -> action -> escalate -> resolve
    """
    if severity not in CYBERBULLYING_SEVERITIES:
        raise ValidationError(
            f"Invalid severity: {severity}. "
            f"Valid severities: {', '.join(sorted(CYBERBULLYING_SEVERITIES))}"
        )

    now = datetime.now(timezone.utc)
    initial_steps = [
        {
            **step,
            "completed": step["step"] == "detect",
            "completed_at": now.isoformat() if step["step"] == "detect" else None,
        }
        for step in CYBERBULLYING_WORKFLOW_STEPS
    ]

    case = CyberbullyingCase(
        id=uuid4(),
        reporter_id=reporter_id,
        target_id=target_id,
        group_id=group_id,
        evidence_ids=evidence_ids,
        severity=severity,
        description=description,
        status="open",
        workflow_steps=initial_steps,
    )
    db.add(case)
    await db.flush()
    await db.refresh(case)

    logger.info(
        "cyberbullying_case_created",
        case_id=str(case.id),
        reporter_id=str(reporter_id),
        target_id=str(target_id),
        severity=severity,
    )
    return case


async def get_cyberbullying_case(
    db: AsyncSession,
    case_id: UUID,
) -> CyberbullyingCase:
    """Get a cyberbullying case by ID."""
    result = await db.execute(
        select(CyberbullyingCase).where(CyberbullyingCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise NotFoundError("Cyberbullying case", str(case_id))
    return case


async def advance_cyberbullying_workflow(
    db: AsyncSession,
    case_id: UUID,
    step_name: str,
    notes: str | None = None,
) -> CyberbullyingCase:
    """Advance a cyberbullying case to the next workflow step."""
    case = await get_cyberbullying_case(db, case_id)

    steps = case.workflow_steps or []
    now = datetime.now(timezone.utc)
    found = False

    for step in steps:
        if step["step"] == step_name:
            step["completed"] = True
            step["completed_at"] = now.isoformat()
            if notes:
                step["notes"] = notes
            found = True
            break

    if not found:
        raise ValidationError(f"Unknown workflow step: {step_name}")

    case.workflow_steps = steps
    # Force SQLAlchemy to detect the change on JSON column
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(case, "workflow_steps")

    await db.flush()
    await db.refresh(case)

    logger.info(
        "cyberbullying_workflow_advanced",
        case_id=str(case_id),
        step=step_name,
    )
    return case


async def close_cyberbullying_case(
    db: AsyncSession,
    case_id: UUID,
    resolution: str,
    notes: str | None = None,
) -> CyberbullyingCase:
    """Close a cyberbullying case with resolution."""
    case = await get_cyberbullying_case(db, case_id)

    if case.status == "closed":
        raise ValidationError("Case is already closed")

    now = datetime.now(timezone.utc)
    case.status = "closed"
    case.resolution = resolution
    case.resolved_at = now

    # Mark resolve step as completed
    steps = case.workflow_steps or []
    for step in steps:
        if step["step"] == "resolve":
            step["completed"] = True
            step["completed_at"] = now.isoformat()
            if notes:
                step["notes"] = notes

    case.workflow_steps = steps
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(case, "workflow_steps")

    await db.flush()
    await db.refresh(case)

    logger.info(
        "cyberbullying_case_closed",
        case_id=str(case_id),
        resolution=resolution,
    )
    return case


async def list_cyberbullying_cases(
    db: AsyncSession,
    group_id: UUID | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[CyberbullyingCase]:
    """List cyberbullying cases with optional filters."""
    query = select(CyberbullyingCase)
    if group_id:
        query = query.where(CyberbullyingCase.group_id == group_id)
    if status:
        query = query.where(CyberbullyingCase.status == status)

    query = query.order_by(CyberbullyingCase.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
