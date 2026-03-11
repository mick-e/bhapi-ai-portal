"""Compliance API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.compliance.export_worker import export_user_data_bytes
from src.compliance.eu_ai_act import (
    get_algorithmic_transparency,
    list_appeals,
    request_human_review,
    resolve_appeal,
    submit_appeal,
)
from src.compliance.schemas import (
    AppealResolve,
    AppealResponse,
    AppealSubmit,
    AuditEntryResponse,
    COPPAComplianceReportResponse,
    COPPAReviewResponse,
    ConsentResponse,
    ConsentWithdrawRequest,
    DataRequestCreate,
    DataRequestStatus,
    HumanReviewResponse,
)
from src.compliance.service import (
    create_data_request,
    get_data_request_status,
    list_audit_entries,
    list_consents,
    withdraw_consent,
)
from src.database import get_db
from src.dependencies import resolve_group_id as _gid
from src.exceptions import ValidationError
from src.schemas import GroupContext

router = APIRouter()


@router.post("/data-request", response_model=DataRequestStatus, status_code=201)
async def create_data_request_endpoint(
    data: DataRequestCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a data deletion/export request (GDPR Article 17, COPPA) (FR-051)."""
    request = await create_data_request(db, auth.user_id, data)
    return request


@router.get("/data-request/{request_id}/status", response_model=DataRequestStatus)
async def get_data_request_status_endpoint(
    request_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get data request status (FR-052)."""
    request = await get_data_request_status(db, request_id)
    return request


@router.get("/data-request/{request_id}/download")
async def download_export(
    request_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a data export as a ZIP file (GDPR Article 20)."""
    request = await get_data_request_status(db, request_id)

    if request.request_type != "data_export":
        raise ValidationError("Only data_export requests can be downloaded")

    # Generate export on-demand
    content = await export_user_data_bytes(db, request.user_id)
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="bhapi_data_export.zip"',
        },
    )


@router.get("/consents", response_model=list[ConsentResponse])
async def list_consents_endpoint(
    group_id: UUID | None = Query(None, description="Group ID"),
    member_id: UUID | None = Query(None, description="Filter by member ID"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List consent records for a group (FR-053)."""
    consents = await list_consents(db, _gid(group_id, auth), member_id=member_id, offset=offset, limit=limit)
    return consents


@router.post("/consent/withdraw", response_model=list[ConsentResponse])
async def withdraw_consent_endpoint(
    data: ConsentWithdrawRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw consent (GDPR Article 7(3))."""
    records = await withdraw_consent(db, auth.user_id, data)
    return records


@router.get("/audit-log", response_model=list[AuditEntryResponse])
async def list_audit_log_endpoint(
    group_id: UUID | None = Query(None, description="Group ID"),
    action: str | None = Query(None, description="Filter by action"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List audit log entries (FR-054)."""
    entries = await list_audit_entries(
        db, _gid(group_id, auth), action=action, resource_type=resource_type, offset=offset, limit=limit
    )
    return entries


@router.post("/coppa/verify-consent")
async def coppa_verify_consent(
    group_id: UUID = Query(...),
    member_id: UUID = Query(...),
    method: str = Query(...),
    evidence: str | None = Query(None),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record verifiable parental consent (COPPA)."""
    from src.compliance.coppa import verify_parental_consent
    record = await verify_parental_consent(db, group_id, member_id, auth.user_id, method, evidence)
    return {"id": str(record.id), "status": "verified", "consent_type": record.consent_type}


@router.get("/coppa/audit-report")
async def coppa_audit_report(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate COPPA compliance audit report."""
    from src.compliance.coppa import generate_coppa_audit_report
    return await generate_coppa_audit_report(db, group_id)


@router.get("/coppa/status")
async def coppa_status(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check COPPA compliance status."""
    from src.compliance.coppa import check_coppa_compliance
    return await check_coppa_compliance(db, group_id)


# ---------------------------------------------------------------------------
# COPPA 2026 Dashboard
# ---------------------------------------------------------------------------


@router.get("/coppa/checklist", response_model=COPPAComplianceReportResponse)
async def coppa_checklist(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return auto-assessed COPPA compliance checklist for a group."""
    from src.compliance.coppa_dashboard import assess_coppa_compliance
    report = await assess_coppa_compliance(db, group_id)
    return {
        "group_id": report.group_id,
        "group_name": report.group_name,
        "score": report.score,
        "status": report.status,
        "checklist": [
            {
                "id": item.id,
                "label": item.label,
                "description": item.description,
                "status": item.status,
                "evidence": item.evidence,
                "action_url": item.action_url,
                "regulation_ref": item.regulation_ref,
            }
            for item in report.checklist
        ],
        "assessed_at": report.assessed_at,
        "last_review": report.last_review,
    }


@router.get("/coppa/export")
async def coppa_export(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export COPPA compliance evidence as a PDF."""
    from src.compliance.coppa_dashboard import export_coppa_evidence
    pdf_bytes = await export_coppa_evidence(db, group_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="coppa_evidence.pdf"',
        },
    )


@router.post("/coppa/review", response_model=COPPAReviewResponse)
async def coppa_review(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark annual COPPA compliance review as complete."""
    from src.compliance.coppa_dashboard import mark_annual_review
    return await mark_annual_review(db, group_id)


# ---------------------------------------------------------------------------
# EU AI Act — algorithmic transparency, human review, appeals
# ---------------------------------------------------------------------------


@router.get("/algorithmic-transparency")
async def algorithmic_transparency_endpoint(
    group_id: UUID | None = Query(None, description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return algorithmic transparency report (EU AI Act)."""
    return await get_algorithmic_transparency(db, _gid(group_id, auth))


@router.post("/human-review/{risk_event_id}", response_model=HumanReviewResponse, status_code=201)
async def request_human_review_endpoint(
    risk_event_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request human review of an automated risk classification (EU AI Act)."""
    review = await request_human_review(
        db, risk_event_id, auth.user_id, _gid(None, auth)
    )
    return review


@router.post("/appeal/{risk_event_id}", response_model=AppealResponse, status_code=201)
async def submit_appeal_endpoint(
    risk_event_id: UUID,
    data: AppealSubmit,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit an appeal against an automated risk classification (EU AI Act Article 22)."""
    appeal = await submit_appeal(
        db, risk_event_id, auth.user_id, _gid(None, auth), data.reason
    )
    return appeal


@router.get("/appeals", response_model=list[AppealResponse])
async def list_appeals_endpoint(
    group_id: UUID | None = Query(None, description="Group ID"),
    status: str | None = Query(None, description="Filter by status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List appeals for a group (EU AI Act)."""
    appeals, _total = await list_appeals(
        db, _gid(group_id, auth), status=status, limit=limit, offset=offset
    )
    return appeals


@router.patch("/appeals/{appeal_id}", response_model=AppealResponse)
async def resolve_appeal_endpoint(
    appeal_id: UUID,
    data: AppealResolve,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve an appeal (admin action, EU AI Act)."""
    appeal = await resolve_appeal(
        db, appeal_id, auth.user_id, data.resolution, data.notes
    )
    return appeal
