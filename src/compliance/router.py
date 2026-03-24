"""Compliance API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.compliance.eu_ai_act import (
    get_algorithmic_transparency,
    list_appeals,
    request_human_review,
    resolve_appeal,
    submit_appeal,
)
from src.compliance.export_worker import export_user_data_bytes
from src.compliance.schemas import (
    AppealResolve,
    AppealResponse,
    AppealSubmit,
    AuditEntryResponse,
    ConsentResponse,
    ConsentWithdrawRequest,
    COPPAComplianceReportResponse,
    COPPAReviewResponse,
    DataRequestCreate,
    DataRequestStatus,
    HumanReviewResponse,
    PushNotificationConsentResponse,
    PushNotificationConsentUpdate,
    RefusePartialCollectionRequest,
    RetentionDisclosureResponse,
    RetentionPolicyResponse,
    RetentionPolicyUpdate,
    ThirdPartyConsentBulkUpdate,
    ThirdPartyConsentItemResponse,
    ThirdPartyConsentUpdate,
    VideoVerificationCreate,
    VideoVerificationResponse,
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
# COPPA 2026 — Parental Data Collection Dashboard
# ---------------------------------------------------------------------------


@router.get("/coppa/data-dashboard")
async def coppa_data_dashboard(
    group_id: UUID = Query(...),
    member_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return parental data collection dashboard for a child member (COPPA 2026).

    Shows parents what data is collected, which third parties have access,
    retention policies, and degraded providers for transparency compliance.
    """
    from src.compliance.coppa_2026 import get_data_dashboard

    return await get_data_dashboard(db, group_id, member_id)


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


# ─── SOC 2 — Audit Initiation (P3-B4) ───────────────────────────────────────


@router.get("/soc2/policies")
async def soc2_list_policies(
    category: str | None = Query(None, description="Filter by category: security/availability/confidentiality/privacy"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List SOC 2 audit policies, optionally filtered by category."""
    from src.compliance.soc2 import get_policies

    policies = await get_policies(db, category=category)
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "category": p.category,
            "description": p.description,
            "version": p.version,
            "effective_date": p.effective_date.isoformat() if p.effective_date else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in policies
    ]


@router.post("/soc2/policies", status_code=201)
async def soc2_create_policy(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new SOC 2 audit policy."""
    from src.compliance.soc2 import create_policy

    if not data.get("name"):
        raise ValidationError("name is required")
    if not data.get("category"):
        raise ValidationError("category is required")

    from datetime import datetime, timezone as tz
    effective_date = None
    if data.get("effective_date"):
        try:
            effective_date = datetime.fromisoformat(data["effective_date"])
            if effective_date.tzinfo is None:
                effective_date = effective_date.replace(tzinfo=tz.utc)
        except (ValueError, TypeError):
            raise ValidationError("effective_date must be a valid ISO 8601 datetime string")

    policy = await create_policy(
        db,
        name=data["name"],
        category=data["category"],
        description=data.get("description"),
        version=data.get("version", "1.0"),
        effective_date=effective_date,
    )
    return {
        "id": str(policy.id),
        "name": policy.name,
        "category": policy.category,
        "description": policy.description,
        "version": policy.version,
        "effective_date": policy.effective_date.isoformat() if policy.effective_date else None,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
    }


@router.get("/soc2/readiness")
async def soc2_readiness_report(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get SOC 2 readiness report — control mapping and overall readiness percentage."""
    from src.compliance.soc2 import get_readiness_report

    return await get_readiness_report(db)


@router.post("/soc2/evidence/collect", status_code=201)
async def soc2_collect_evidence(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger SOC 2 evidence collection (admin only)."""
    from src.compliance.soc2 import collect_evidence

    items = await collect_evidence(db)
    return {
        "collected": len(items),
        "evidence": [
            {
                "id": str(e.id),
                "evidence_type": e.evidence_type,
                "collected_at": e.collected_at.isoformat() if e.collected_at else None,
            }
            for e in items
        ],
    }


@router.put("/soc2/controls/{control_id}")
async def soc2_update_control(
    control_id: str,
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update or create a SOC 2 compliance control status."""
    from src.compliance.soc2 import update_control_status

    if not data.get("status"):
        raise ValidationError("status is required")

    control = await update_control_status(
        db,
        control_id=control_id,
        status=data["status"],
        description=data.get("description"),
        evidence_ids=data.get("evidence_ids"),
    )
    return {
        "id": str(control.id),
        "control_id": control.control_id,
        "description": control.description,
        "status": control.status,
        "evidence_ids": control.evidence_ids or [],
        "created_at": control.created_at.isoformat() if control.created_at else None,
    }


# ─── SOC 2 & Audit ─────────────────────────────────────────────────────────


@router.get("/audit-logs")
async def get_audit_logs(
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit logs."""
    from src.compliance.audit_logger import query_audit_logs

    gid = _gid(None, auth)
    offset = (page - 1) * page_size
    logs, total = await query_audit_logs(
        db, group_id=gid, action=action,
        resource_type=resource_type, limit=page_size, offset=offset,
    )
    return {
        "items": [
            {
                "id": str(log.id),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "actor_email": log.actor_email,
                "created_at": (
                    log.created_at.isoformat() if log.created_at else None
                ),
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/soc2-evidence")
async def get_soc2_evidence(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get SOC 2 evidence summary."""
    from src.compliance.soc2_evidence import get_soc2_evidence_summary

    gid = _gid(None, auth)
    return await get_soc2_evidence_summary(db, gid)


@router.post("/incidents", status_code=201)
async def create_incident_endpoint(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a security incident record."""
    from src.compliance.incident import create_incident

    gid = _gid(None, auth)
    incident = await create_incident(
        db, title=data.get("title", ""), severity=data.get("severity", "medium"),
        category=data.get("category", "security"), description=data.get("description", ""),
        group_id=gid, reported_by=auth.user_id,
    )
    return {"id": str(incident.id), "title": incident.title, "status": incident.status}


@router.get("/incidents")
async def list_incidents_endpoint(
    status: str | None = Query(None),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List security incidents."""
    from src.compliance.incident import list_incidents

    gid = _gid(None, auth)
    incidents = await list_incidents(db, group_id=gid, status=status)
    return {"incidents": [
        {"id": str(i.id), "title": i.title, "severity": i.severity,
         "category": i.category, "status": i.status,
         "created_at": i.created_at.isoformat() if i.created_at else None}
        for i in incidents
    ]}


@router.patch("/incidents/{incident_id}")
async def update_incident_endpoint(
    incident_id: str,
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update incident status."""
    from uuid import UUID as UUIDType

    from src.compliance.incident import update_incident_status

    incident = await update_incident_status(
        db, UUIDType(incident_id), status=data.get("status", ""),
        resolution=data.get("resolution"), root_cause=data.get("root_cause"),
    )
    return {"id": str(incident.id), "status": incident.status}


# ─── COPPA 2026 — Third-Party Data Flow Consent ──────────────────────────────


@router.get(
    "/coppa/third-party-consent",
    response_model=list[ThirdPartyConsentItemResponse],
)
async def get_third_party_consent(
    group_id: UUID = Query(...),
    member_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get per-third-party consent items for a member (COPPA 2026)."""
    from src.compliance.coppa_2026 import get_third_party_consents

    items = await get_third_party_consents(db, group_id, member_id)
    return items


@router.put("/coppa/third-party-consent", response_model=ThirdPartyConsentItemResponse)
async def update_third_party_consent_endpoint(
    group_id: UUID = Query(...),
    member_id: UUID = Query(...),
    data: ThirdPartyConsentUpdate = ...,
    request: Request = ...,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update consent for a specific third-party provider (COPPA 2026)."""
    from src.compliance.coppa_2026 import update_third_party_consent

    ip = request.client.host if request.client else None
    item = await update_third_party_consent(
        db, group_id, member_id, auth.user_id,
        data.provider_key, data.consented, ip,
    )
    return item


@router.put(
    "/coppa/third-party-consent/bulk",
    response_model=list[ThirdPartyConsentItemResponse],
)
async def bulk_update_third_party_consent_endpoint(
    group_id: UUID = Query(...),
    data: ThirdPartyConsentBulkUpdate = ...,
    request: Request = ...,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk update third-party consent for a member (COPPA 2026)."""
    from src.compliance.coppa_2026 import bulk_update_third_party_consent

    ip = request.client.host if request.client else None
    items = await bulk_update_third_party_consent(
        db, group_id, data.member_id, auth.user_id,
        [c.model_dump() for c in data.consents], ip,
    )
    return items


@router.post(
    "/coppa/refuse-partial-collection",
    response_model=list[ThirdPartyConsentItemResponse],
)
async def refuse_partial_collection_endpoint(
    group_id: UUID = Query(...),
    data: RefusePartialCollectionRequest = ...,
    request: Request = ...,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Refuse third-party data sharing while allowing collection (COPPA 2026)."""
    from src.compliance.coppa_2026 import set_refuse_partial_collection

    ip = request.client.host if request.client else None
    items = await set_refuse_partial_collection(
        db, group_id, data.member_id, auth.user_id,
        data.refuse_third_party_sharing, ip,
    )
    return items


# ─── COPPA 2026 — Retention Policies ─────────────────────────────────────────


@router.get("/coppa/retention", response_model=list[RetentionPolicyResponse])
async def get_retention_policies_endpoint(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get data retention policies for a group (COPPA 2026)."""
    from src.compliance.retention import get_retention_policies

    policies = await get_retention_policies(db, group_id)
    return policies


@router.put("/coppa/retention", response_model=RetentionPolicyResponse)
async def update_retention_policy_endpoint(
    group_id: UUID = Query(...),
    data: RetentionPolicyUpdate = ...,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a retention policy (COPPA 2026)."""
    from src.compliance.retention import update_retention_policy

    policy = await update_retention_policy(
        db, group_id, data.data_type, data.retention_days, data.auto_delete,
    )
    return policy


@router.get("/coppa/retention/disclosure", response_model=RetentionDisclosureResponse)
async def get_retention_disclosure_endpoint(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get parent-facing data retention disclosure (COPPA 2026)."""
    from src.compliance.retention import get_retention_disclosure

    disclosure = await get_retention_disclosure(db, group_id)
    return disclosure


# ─── COPPA 2026 — Push Notification Consent ──────────────────────────────────


@router.get(
    "/coppa/push-consent",
    response_model=list[PushNotificationConsentResponse],
)
async def get_push_notification_consents_endpoint(
    group_id: UUID = Query(...),
    member_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get push notification consent records for a member (COPPA 2026)."""
    from src.compliance.coppa_2026 import get_push_notification_consents

    consents = await get_push_notification_consents(db, group_id, member_id)
    return consents


@router.put("/coppa/push-consent", response_model=PushNotificationConsentResponse)
async def update_push_notification_consent_endpoint(
    group_id: UUID = Query(...),
    data: PushNotificationConsentUpdate = ...,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update push notification consent (COPPA 2026)."""
    from src.compliance.coppa_2026 import update_push_notification_consent

    consent = await update_push_notification_consent(
        db, group_id, data.member_id, auth.user_id,
        data.notification_type, data.consented,
    )
    return consent


# ─── COPPA 2026 — Video Verification (Enhanced VPC) ──────────────────────────


@router.post(
    "/coppa/video-verification",
    response_model=VideoVerificationResponse,
    status_code=201,
)
async def initiate_video_verification_endpoint(
    group_id: UUID = Query(...),
    data: VideoVerificationCreate = ...,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate video-based parental identity verification (COPPA 2026)."""
    from src.compliance.coppa_2026 import initiate_video_verification

    verification = await initiate_video_verification(
        db, group_id, auth.user_id, data.verification_method,
    )
    return verification


@router.get(
    "/coppa/video-verification/{verification_id}",
    response_model=VideoVerificationResponse,
)
async def get_video_verification_endpoint(
    verification_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get video verification status (COPPA 2026)."""
    from src.compliance.coppa_2026 import get_video_verification

    return await get_video_verification(db, verification_id)


@router.patch(
    "/coppa/video-verification/{verification_id}",
    response_model=VideoVerificationResponse,
)
async def complete_video_verification_endpoint(
    verification_id: UUID,
    score: float = Query(..., ge=0.0, le=1.0),
    notes: str | None = Query(None),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete a video verification with a score (COPPA 2026)."""
    from src.compliance.coppa_2026 import complete_video_verification

    return await complete_video_verification(db, verification_id, score, notes)


@router.get(
    "/coppa/video-verifications",
    response_model=list[VideoVerificationResponse],
)
async def list_video_verifications_endpoint(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List video verifications for the current parent (COPPA 2026)."""
    from src.compliance.coppa_2026 import get_parent_verifications

    return await get_parent_verifications(db, group_id, auth.user_id)


# ─── COPPA 2026 — Safe Harbor Certificate ─────────────────────────────────


@router.get("/coppa/safe-harbor-certificate")
async def get_safe_harbor_certificate(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate COPPA safe harbor compliance certificate data (COPPA 2026)."""
    from src.compliance.coppa_2026 import generate_safe_harbor_certificate

    return await generate_safe_harbor_certificate(db, group_id)


@router.get("/coppa/safe-harbor-certificate/pdf")
async def get_safe_harbor_certificate_pdf(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download COPPA safe harbor compliance certificate as PDF (COPPA 2026)."""
    from src.compliance.coppa_2026 import generate_safe_harbor_certificate_pdf

    pdf_bytes = await generate_safe_harbor_certificate_pdf(db, group_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="coppa_safe_harbor_certificate.pdf"',
        },
    )


# ─── UK AADC — Gap Analysis & Privacy-by-Default ─────────────────────────────


@router.post("/uk/aadc/gap-analysis")
async def run_aadc_gap_analysis(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run UK AADC gap analysis for a group."""
    from src.compliance.uk_aadc import run_gap_analysis

    return await run_gap_analysis(db, group_id, assessor=str(auth.user_id))


@router.get("/uk/aadc/gap-analysis")
async def get_aadc_gap_analysis(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get latest AADC gap analysis for a group."""
    from src.compliance.uk_aadc import get_latest_assessment

    result = await get_latest_assessment(db, group_id)
    if not result:
        return {"message": "No AADC assessment found. Run a gap analysis first."}
    return result


@router.get("/uk/aadc/privacy-defaults")
async def get_aadc_privacy_defaults(
    age_tier: str = Query(..., description="Age tier: young, preteen, or teen"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AADC privacy-by-default settings for an age tier."""
    from src.compliance.uk_aadc import get_default_privacy_settings

    return get_default_privacy_settings(age_tier)


@router.post("/uk/aadc/apply-defaults")
async def apply_aadc_defaults(
    user_id: UUID = Query(...),
    age_tier: str = Query(..., description="Age tier: young, preteen, or teen"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply AADC privacy-by-default settings to a user."""
    from src.compliance.uk_aadc import apply_privacy_defaults

    return await apply_privacy_defaults(db, user_id, age_tier)


@router.get("/uk/aadc/assessment-history")
async def get_aadc_assessment_history(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all AADC gap analysis assessments for a group."""
    from src.compliance.uk_aadc import get_assessment_history

    return await get_assessment_history(db, group_id)


@router.get("/coppa/video-verification-status")
async def check_video_verification_status(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if parent has valid video verification (COPPA 2026)."""
    from src.compliance.coppa_2026 import has_valid_video_verification

    has_valid = await has_valid_video_verification(db, group_id, auth.user_id)
    return {"group_id": str(group_id), "has_valid_verification": has_valid}


# ─── Australian Online Safety ────────────────────────────────────────────────


@router.get("/au/age-requirement")
async def au_age_requirement_endpoint(
    user_id: UUID = Query(...),
    country_code: str = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check AU age verification requirement for social access."""
    from src.compliance.australian import check_au_age_requirement

    return await check_au_age_requirement(db, user_id, country_code)


@router.post("/au/age-verification", status_code=201)
async def au_create_age_verification_endpoint(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create age verification record for an AU user."""
    from src.compliance.australian import create_age_verification

    record = await create_age_verification(
        db,
        user_id=auth.user_id,
        country_code=data.get("country_code", "AU"),
        method=data.get("method", ""),
        verification_data=data.get("verification_data"),
    )
    return {
        "id": str(record.id),
        "user_id": str(record.user_id),
        "method": record.method,
        "verified": record.verified,
        "verified_at": record.verified_at.isoformat() if record.verified_at else None,
    }


@router.get("/au/esafety-sla")
async def au_esafety_sla_endpoint(
    group_id: UUID | None = Query(None),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check eSafety 24-hour SLA compliance status."""
    from src.compliance.australian import check_esafety_sla

    return await check_esafety_sla(db, group_id)


@router.get("/au/esafety-report")
async def au_esafety_report_endpoint(
    group_id: UUID | None = Query(None),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate eSafety Commissioner compliance report."""
    from src.compliance.australian import get_esafety_report

    return await get_esafety_report(db, group_id)


@router.post("/au/cyberbullying-case", status_code=201)
async def au_create_cyberbullying_case_endpoint(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a structured cyberbullying case."""
    from src.compliance.australian import create_cyberbullying_case

    if "reporter_id" not in data or "target_id" not in data:
        raise ValidationError("reporter_id and target_id are required")

    try:
        reporter_id = UUID(data["reporter_id"])
        target_id = UUID(data["target_id"])
        group_id = UUID(data["group_id"]) if data.get("group_id") else None
    except (ValueError, AttributeError):
        raise ValidationError("Invalid UUID format for reporter_id, target_id, or group_id")

    case = await create_cyberbullying_case(
        db,
        reporter_id=reporter_id,
        target_id=target_id,
        evidence_ids=data.get("evidence_ids", []),
        severity=data.get("severity", "medium"),
        description=data.get("description"),
        group_id=group_id,
    )
    return {
        "id": str(case.id),
        "reporter_id": str(case.reporter_id),
        "target_id": str(case.target_id),
        "severity": case.severity,
        "status": case.status,
        "workflow_steps": case.workflow_steps,
    }


@router.get("/au/cyberbullying-case/{case_id}")
async def au_get_cyberbullying_case_endpoint(
    case_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a cyberbullying case by ID."""
    from src.compliance.australian import get_cyberbullying_case

    case = await get_cyberbullying_case(db, case_id)
    return {
        "id": str(case.id),
        "reporter_id": str(case.reporter_id),
        "target_id": str(case.target_id),
        "severity": case.severity,
        "status": case.status,
        "description": case.description,
        "evidence_ids": case.evidence_ids,
        "workflow_steps": case.workflow_steps,
        "resolution": case.resolution,
        "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None,
        "created_at": case.created_at.isoformat() if case.created_at else None,
    }


@router.patch("/au/cyberbullying-case/{case_id}/workflow")
async def au_advance_cyberbullying_workflow_endpoint(
    case_id: UUID,
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Advance a cyberbullying case workflow step."""
    from src.compliance.australian import advance_cyberbullying_workflow

    case = await advance_cyberbullying_workflow(
        db, case_id, step_name=data["step"], notes=data.get("notes"),
    )
    return {
        "id": str(case.id),
        "status": case.status,
        "workflow_steps": case.workflow_steps,
    }


@router.post("/au/cyberbullying-case/{case_id}/close")
async def au_close_cyberbullying_case_endpoint(
    case_id: UUID,
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Close a cyberbullying case with resolution."""
    from src.compliance.australian import close_cyberbullying_case

    case = await close_cyberbullying_case(
        db, case_id, resolution=data["resolution"], notes=data.get("notes"),
    )
    return {
        "id": str(case.id),
        "status": case.status,
        "resolution": case.resolution,
        "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None,
    }
