"""Alerts API endpoints."""

import asyncio
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from src.alerts.models import Alert
from src.alerts.panic import PanicReport as _PanicReport  # noqa: F401 — register model
from src.alerts.schemas import (
    AlertUpdateRequest,
    PreferenceResponse,
    PreferenceUpdate,
)
from src.alerts.service import (
    get_alert,
    get_preferences,
    get_unified_alerts,
    update_preferences,
)
from src.alerts.sse import sse_manager
from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription
from src.dependencies import resolve_group_id as _gid
from src.groups.models import GroupMember
from src.schemas import GroupContext

router = APIRouter(dependencies=[Depends(require_active_trial_or_subscription)])

# Backend → frontend severity mapping
_SEVERITY_MAP = {
    "critical": "critical",
    "high": "error",
    "medium": "warning",
    "low": "info",
    "info": "info",
}


def _alert_to_frontend(alert: Alert, member_names: dict[UUID, str]) -> dict:
    """Convert a backend Alert to the frontend Alert shape."""
    return {
        "id": str(alert.id),
        "group_id": str(alert.group_id),
        "type": "risk" if alert.risk_event_id else "system",
        "source": getattr(alert, "source", "ai") or "ai",
        "severity": _SEVERITY_MAP.get(alert.severity, "info"),
        "title": alert.title,
        "message": alert.body,
        "member_name": member_names.get(alert.member_id) if alert.member_id else None,
        "read": alert.status == "acknowledged",
        "actioned": alert.status == "acknowledged",
        "related_member_id": str(alert.member_id) if alert.member_id else None,
        "related_event_id": str(alert.risk_event_id) if alert.risk_event_id else None,
        "snoozed_until": alert.snoozed_until.isoformat() if alert.snoozed_until else None,
        "created_at": alert.created_at.isoformat() if alert.created_at else "",
    }


@router.get("")
async def list_alerts_endpoint(
    group_id: UUID | None = Query(None, description="Group ID (defaults to user's primary group)"),
    severity: str | None = Query(None, description="Filter by severity"),
    type: str | None = Query(None, description="Filter by type"),
    read: bool | None = Query(None, description="Filter by read status"),
    start_date: date | None = Query(None, description="Filter alerts from this date (inclusive)"),
    end_date: date | None = Query(None, description="Filter alerts until this date (inclusive)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List alerts for a group with pagination matching frontend PaginatedResponse."""
    gid = _gid(group_id, auth)

    base = select(Alert).where(Alert.group_id == gid)
    count_q = select(func.count(Alert.id)).where(Alert.group_id == gid)

    if start_date:
        start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        base = base.where(Alert.created_at >= start_dt)
        count_q = count_q.where(Alert.created_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        base = base.where(Alert.created_at <= end_dt)
        count_q = count_q.where(Alert.created_at <= end_dt)

    # Map frontend severity names back to backend
    if severity:
        reverse_map = {"critical": "critical", "error": "high", "warning": "medium", "info": ["low", "info"]}
        backend_sev = reverse_map.get(severity, severity)
        if isinstance(backend_sev, list):
            base = base.where(Alert.severity.in_(backend_sev))
            count_q = count_q.where(Alert.severity.in_(backend_sev))
        else:
            base = base.where(Alert.severity == backend_sev)
            count_q = count_q.where(Alert.severity == backend_sev)

    if read is not None:
        if read:
            base = base.where(Alert.status == "acknowledged")
            count_q = count_q.where(Alert.status == "acknowledged")
        else:
            base = base.where(Alert.status != "acknowledged")
            count_q = count_q.where(Alert.status != "acknowledged")

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size
    rows = await db.execute(
        base.order_by(Alert.created_at.desc()).offset(offset).limit(page_size)
    )
    alerts = list(rows.scalars().all())

    # Member name lookup
    member_ids = {a.member_id for a in alerts if a.member_id}
    member_names: dict[UUID, str] = {}
    if member_ids:
        mr = await db.execute(
            select(GroupMember.id, GroupMember.display_name).where(
                GroupMember.id.in_(member_ids)
            )
        )
        member_names = {row[0]: row[1] for row in mr.all()}

    items = [_alert_to_frontend(a, member_names) for a in alerts]
    total_pages = max((total + page_size - 1) // page_size, 1)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/unified")
async def unified_alerts_endpoint(
    group_id: UUID | None = Query(None, description="Group ID (defaults to user's primary group)"),
    member_id: UUID | None = Query(None, description="Filter by member ID"),
    source: str | None = Query(None, description="Filter by source: ai, social, device"),
    severity: str | None = Query(None, description="Filter by severity"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unified alert feed across AI, social, and device sources.

    Returns alerts sorted by severity (critical first) then timestamp (newest first).
    Supports filtering by source (ai|social|device) and member_id.
    """
    gid = _gid(group_id, auth)
    result = await get_unified_alerts(
        db, gid,
        member_id=member_id,
        source_filter=source,
        page=page,
        page_size=page_size,
    )

    alerts = result["items"]

    # Apply severity filter if provided
    if severity:
        reverse_map = {"critical": "critical", "error": "high", "warning": "medium", "info": ["low", "info"]}
        backend_sev = reverse_map.get(severity, severity)
        if isinstance(backend_sev, list):
            alerts = [a for a in alerts if a.severity in backend_sev]
        else:
            alerts = [a for a in alerts if a.severity == backend_sev]

    # Member name lookup
    member_ids = {a.member_id for a in alerts if a.member_id}
    member_names: dict[UUID, str] = {}
    if member_ids:
        mr = await db.execute(
            select(GroupMember.id, GroupMember.display_name).where(
                GroupMember.id.in_(member_ids)
            )
        )
        member_names = {row[0]: row[1] for row in mr.all()}

    items = [_alert_to_frontend(a, member_names) for a in alerts]

    return {
        "items": items,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"],
    }


@router.get("/stream")
async def alert_stream(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE endpoint for real-time alert notifications."""
    queue = sse_manager.connect(group_id)

    async def event_generator():
        try:
            # Send initial keepalive
            yield ": keepalive\n\n"
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield message
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.disconnect(group_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Static paths MUST come before /{alert_id}
@router.get("/preferences", response_model=list[PreferenceResponse])
async def get_preferences_endpoint(
    group_id: UUID | None = Query(None, description="Group ID (defaults to user's primary group)"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notification preferences for the current user in a group."""
    prefs = await get_preferences(db, _gid(group_id, auth), auth.user_id)
    return prefs


@router.put("/preferences", response_model=list[PreferenceResponse])
async def update_preferences_endpoint(
    data: PreferenceUpdate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update notification preferences (FR-023)."""
    prefs = await update_preferences(db, data.group_id, auth.user_id, data.preferences)
    return prefs


@router.post("/mark-all-read", status_code=204)
async def mark_all_read(
    group_id: UUID | None = Query(None, description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all alerts as read for a group."""
    gid = _gid(group_id, auth)
    await db.execute(
        update(Alert)
        .where(Alert.group_id == gid, Alert.status != "acknowledged")
        .values(
            status="acknowledged",
            acknowledged_at=datetime.now(timezone.utc),
            acknowledged_by=auth.user_id,
        )
    )
    await db.flush()
    return None


# --- Panic Button endpoints ---
# Static routes MUST come before /{alert_id}


class PanicReportCreate(BaseModel):
    """Create a panic report."""
    group_id: UUID
    member_id: UUID
    category: str = Field(pattern="^(scary_content|weird_request|bad_ai_response|other)$")
    message: str | None = Field(None, max_length=500)
    platform: str | None = None
    session_id: str | None = None


class PanicReportResponse(BaseModel):
    """Panic report response."""
    id: UUID
    group_id: UUID
    member_id: UUID
    category: str
    message: str | None = None
    platform: str | None = None
    session_id: str | None = None
    parent_response: str | None = None
    parent_responded_at: datetime | None = None
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PanicRespondRequest(BaseModel):
    """Parent response to a panic report."""
    response: str = Field(min_length=1, max_length=500)


@router.post("/panic", response_model=PanicReportResponse, status_code=201)
async def create_panic(
    data: PanicReportCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Child submits a panic report."""
    from src.alerts.panic import create_panic_report

    report = await create_panic_report(
        db,
        group_id=data.group_id,
        member_id=data.member_id,
        category=data.category,
        message=data.message,
        platform=data.platform,
        session_id=data.session_id,
    )
    return report


@router.get("/panic")
async def list_panics(
    group_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List panic reports for a group."""
    from src.alerts.panic import list_panic_reports

    gid = _gid(group_id, auth)
    result = await list_panic_reports(db, gid, page, page_size)

    # Serialize PanicReport objects to dicts
    items = []
    for report in result["items"]:
        items.append({
            "id": str(report.id),
            "group_id": str(report.group_id),
            "member_id": str(report.member_id),
            "category": report.category,
            "message": report.message,
            "platform": report.platform,
            "session_id": report.session_id,
            "parent_response": report.parent_response,
            "parent_responded_at": report.parent_responded_at.isoformat() if report.parent_responded_at else None,
            "resolved": report.resolved,
            "created_at": report.created_at.isoformat() if report.created_at else "",
        })

    return {
        "items": items,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"],
    }


@router.get("/panic/quick-responses")
async def get_quick_responses(
    auth: GroupContext = Depends(get_current_user),
):
    """List quick response templates for panic reports."""
    from src.alerts.panic import PARENT_QUICK_RESPONSES

    return {"responses": PARENT_QUICK_RESPONSES}


@router.post("/panic/{report_id}/respond", response_model=PanicReportResponse)
async def respond_panic(
    report_id: UUID,
    data: PanicRespondRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Parent responds to a panic report."""
    from src.alerts.panic import respond_to_panic

    report = await respond_to_panic(db, report_id, auth.user_id, data.response)
    return report


# ─── Push Notifications ─────────────────────────────────────────────────────


@router.post("/push/subscribe", status_code=201)
async def subscribe_push_endpoint(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Subscribe to web push notifications."""
    from src.alerts.web_push import subscribe_push
    gid = _gid(None, auth)
    sub = await subscribe_push(
        db, user_id=auth.user_id, group_id=gid,
        endpoint=data.get("endpoint", ""),
        p256dh_key=data.get("p256dh_key", ""),
        auth_key=data.get("auth_key", ""),
        user_agent=data.get("user_agent"),
    )
    return {"id": str(sub.id), "active": sub.active}


@router.post("/push/unsubscribe")
async def unsubscribe_push_endpoint(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unsubscribe from push notifications."""
    from src.alerts.web_push import unsubscribe_push
    await unsubscribe_push(db, user_id=auth.user_id, endpoint=data.get("endpoint", ""))
    return {"status": "unsubscribed"}


@router.get("/push/subscriptions")
async def list_push_subscriptions(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List active push subscriptions."""
    from src.alerts.web_push import get_user_subscriptions
    subs = await get_user_subscriptions(db, auth.user_id)
    return {"subscriptions": [
        {"id": str(s.id), "endpoint": s.endpoint[:50] + "...", "active": s.active}
        for s in subs
    ]}


# ─── Expo Push Tokens (Mobile) ───────────────────────────────────────────────


class PushTokenRequest(BaseModel):
    """Register an Expo push token."""
    token: str = Field(min_length=1, max_length=255)
    device_type: str = Field(pattern="^(ios|android)$")


@router.post("/push/token", status_code=201)
async def register_push_token(
    data: PushTokenRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register an Expo push token for the current user's mobile device."""
    from src.alerts.push import expo_push_service
    pt = await expo_push_service.register_token(
        db, user_id=auth.user_id, token=data.token, device_type=data.device_type,
    )
    return {"id": str(pt.id), "token": pt.token, "device_type": pt.device_type}


class PushTokenDeleteRequest(BaseModel):
    """Remove an Expo push token."""
    token: str = Field(min_length=1, max_length=255)


@router.delete("/push/token")
async def unregister_push_token(
    data: PushTokenDeleteRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an Expo push token for the current user."""
    from src.alerts.push import expo_push_service
    removed = await expo_push_service.unregister_token(db, user_id=auth.user_id, token=data.token)
    return {"removed": removed}


@router.get("/push/tokens")
async def list_push_tokens(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List registered Expo push tokens for the current user."""
    from src.alerts.push import expo_push_service
    tokens = await expo_push_service.get_user_tokens(db, auth.user_id)
    return {"tokens": [
        {"id": str(t.id), "token": t.token, "device_type": t.device_type}
        for t in tokens
    ]}


# ─── Escalation Partners ────────────────────────────────────────────────────


@router.post("/escalation/partners", status_code=201)
async def create_partner(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an escalation partner."""
    from src.alerts.escalation import create_escalation_partner
    gid = _gid(None, auth)
    partner = await create_escalation_partner(
        db, group_id=gid, name=data.get("name", ""),
        provider_type=data.get("provider_type", ""),
        webhook_url=data.get("webhook_url"),
        contact_email=data.get("contact_email"),
        contact_phone=data.get("contact_phone"),
        severity_threshold=data.get("severity_threshold", "critical"),
        categories=data.get("categories"),
    )
    return {
        "id": str(partner.id), "name": partner.name,
        "provider_type": partner.provider_type, "active": partner.active,
    }


@router.get("/escalation/partners")
async def list_partners(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List escalation partners."""
    from src.alerts.escalation import list_escalation_partners
    gid = _gid(None, auth)
    partners = await list_escalation_partners(db, gid)
    return {"partners": [
        {"id": str(p.id), "name": p.name, "provider_type": p.provider_type, "active": p.active}
        for p in partners
    ]}


@router.post("/escalation/escalate")
async def escalate_alert_endpoint(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Escalate an alert to a partner."""
    from uuid import UUID as UUIDType

    from src.alerts.escalation import escalate_alert
    gid = _gid(None, auth)
    record = await escalate_alert(
        db, partner_id=UUIDType(data["partner_id"]),
        alert_id=UUIDType(data["alert_id"]),
        group_id=gid, severity=data.get("severity", "critical"),
        member_id=UUIDType(data["member_id"]) if data.get("member_id") else None,
        category=data.get("category"),
    )
    return {"id": str(record.id), "status": record.status}


# ─── Alert Correlations ─────────────────────────────────────────────────────


@router.get("/correlations")
async def list_correlations_endpoint(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List alert correlations."""
    from src.alerts.correlation import list_correlations
    gid = _gid(None, auth)
    correlations = await list_correlations(db, gid)
    return {"correlations": [
        {"id": str(c.id), "type": c.correlation_type, "title": c.title,
         "confidence": c.confidence_score, "severity": c.severity}
        for c in correlations
    ]}


@router.get("/correlations/{member_id}")
async def get_member_correlations(
    member_id: str,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get correlations for a member."""
    from uuid import UUID as UUIDType

    from src.alerts.correlation import analyze_member_correlations
    gid = _gid(None, auth)
    return await analyze_member_correlations(db, gid, UUIDType(member_id))


# --- Dynamic {alert_id} routes MUST come after all static paths ---


@router.get("/{alert_id}")
async def get_alert_endpoint(
    alert_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific alert."""
    alert = await get_alert(db, alert_id)
    return _alert_to_frontend(alert, {})


@router.patch("/{alert_id}")
async def update_alert(
    alert_id: UUID,
    body: AlertUpdateRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update alert read/actioned status (frontend PATCH)."""
    alert = await get_alert(db, alert_id)
    if body.read or body.actioned:
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = auth.user_id
    await db.flush()
    await db.refresh(alert)
    return _alert_to_frontend(alert, {})


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert_endpoint(
    alert_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge an alert (FR-022)."""
    from src.alerts.service import acknowledge_alert
    alert = await acknowledge_alert(db, alert_id, auth.user_id)
    return _alert_to_frontend(alert, {})


class SnoozeRequest(BaseModel):
    """Snooze an alert for a duration."""
    hours: int = Field(ge=1, le=168, description="Number of hours to snooze (1-168)")


@router.post("/{alert_id}/snooze")
async def snooze_alert(
    alert_id: UUID,
    data: SnoozeRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Snooze an alert for a specified number of hours."""
    alert = await get_alert(db, alert_id)
    alert.snoozed_until = datetime.now(timezone.utc) + timedelta(hours=data.hours)
    await db.flush()
    await db.refresh(alert)
    return _alert_to_frontend(alert, {})
