"""Data export worker — generates ZIP with JSON exports of all user data.

Implements GDPR Article 20 (right to data portability). Creates a ZIP file
containing JSON exports of all user-related data across tables.
"""

from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert, NotificationPreference
from src.auth.models import User
from src.billing.models import SpendRecord
from src.capture.models import CaptureEvent
from src.compliance.models import AuditEntry, ConsentRecord, DataDeletionRequest
from src.groups.models import Group, GroupMember
from src.risk.models import RiskEvent

logger = structlog.get_logger()

# Export output directory
EXPORTS_DIR = Path(os.environ.get("EXPORTS_DIR", "data/exports"))


def _ensure_exports_dir() -> Path:
    """Ensure the exports directory exists."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORTS_DIR


def _serialize(obj) -> str:
    """JSON serialize with datetime handling."""
    def default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, UUID):
            return str(o)
        return str(o)
    return json.dumps(obj, default=default, indent=2, ensure_ascii=False)


async def process_pending_exports(db: AsyncSession) -> int:
    """Process all pending data export requests.

    Returns the number of requests completed.
    """
    result = await db.execute(
        select(DataDeletionRequest).where(
            DataDeletionRequest.status == "pending",
            DataDeletionRequest.request_type == "data_export",
        )
    )
    requests = list(result.scalars().all())

    completed = 0
    for request in requests:
        try:
            request.status = "processing"
            await db.flush()

            file_path = await _export_user_data(db, request.user_id)

            request.status = "completed"
            request.completed_at = datetime.now(timezone.utc)
            await db.flush()

            # Get a valid group_id for audit trail
            from src.groups.models import GroupMember as GM
            member_result = await db.execute(
                select(GM.group_id).where(GM.user_id == request.user_id).limit(1)
            )
            audit_group_id = member_result.scalar()

            if not audit_group_id:
                from src.groups.models import Group as GroupModel
                group_result = await db.execute(
                    select(GroupModel.id).where(GroupModel.owner_id == request.user_id).limit(1)
                )
                audit_group_id = group_result.scalar()

            # Audit trail (only if we have a valid group)
            if audit_group_id:
                audit = AuditEntry(
                    id=uuid4(),
                    group_id=audit_group_id,
                    actor_id=request.user_id,
                    action="data_export.completed",
                    resource_type="user",
                    resource_id=str(request.user_id),
                    details={"file_path": str(file_path)},
                )
                db.add(audit)
                await db.flush()

            completed += 1
            logger.info(
                "export_completed",
                request_id=str(request.id),
                user_id=str(request.user_id),
                file_path=str(file_path),
            )
        except Exception as exc:
            logger.error(
                "export_failed",
                request_id=str(request.id),
                user_id=str(request.user_id),
                error=str(exc),
            )

    logger.info("export_batch_completed", total=len(requests), completed=completed)
    return completed


async def _export_user_data(db: AsyncSession, user_id: UUID) -> Path:
    """Generate a ZIP file with all user data. Returns the file path."""
    data = await _collect_user_data(db, user_id)
    return _write_zip(user_id, data)


async def export_user_data_bytes(db: AsyncSession, user_id: UUID) -> bytes:
    """Generate a ZIP file in memory. Returns bytes."""
    data = await _collect_user_data(db, user_id)
    return _write_zip_bytes(data)


async def _collect_user_data(db: AsyncSession, user_id: UUID) -> dict:
    """Collect all user data into a dictionary structure."""
    sections: dict[str, list | dict] = {}

    # 1. User profile
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user:
        sections["profile"] = {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "account_type": user.account_type,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat() if hasattr(user, "created_at") and user.created_at else None,
        }

    # 2. Group memberships
    member_result = await db.execute(
        select(GroupMember).where(GroupMember.user_id == user_id)
    )
    members = list(member_result.scalars().all())
    member_ids = [m.id for m in members]

    sections["memberships"] = [
        {
            "id": str(m.id),
            "group_id": str(m.group_id),
            "role": m.role,
            "display_name": m.display_name,
        }
        for m in members
    ]

    # 3. Groups owned
    group_result = await db.execute(
        select(Group).where(Group.owner_id == user_id)
    )
    groups = list(group_result.scalars().all())
    sections["groups_owned"] = [
        {
            "id": str(g.id),
            "name": g.name,
            "type": g.type,
        }
        for g in groups
    ]

    # 4. Capture events (AI interactions)
    if member_ids:
        capture_result = await db.execute(
            select(CaptureEvent).where(CaptureEvent.member_id.in_(member_ids))
            .order_by(CaptureEvent.timestamp.desc())
        )
        captures = list(capture_result.scalars().all())
        sections["capture_events"] = [
            {
                "id": str(c.id),
                "platform": c.platform,
                "event_type": c.event_type,
                "timestamp": c.timestamp.isoformat() if c.timestamp else None,
                "source_channel": c.source_channel,
            }
            for c in captures
        ]

        # 5. Risk events
        risk_result = await db.execute(
            select(RiskEvent).where(RiskEvent.member_id.in_(member_ids))
            .order_by(RiskEvent.created_at.desc())
        )
        risks = list(risk_result.scalars().all())
        sections["risk_events"] = [
            {
                "id": str(r.id),
                "category": r.category,
                "severity": r.severity,
                "confidence": r.confidence,
                "acknowledged": r.acknowledged,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in risks
        ]

        # 6. Alerts
        alert_result = await db.execute(
            select(Alert).where(Alert.member_id.in_(member_ids))
            .order_by(Alert.created_at.desc())
        )
        alerts = list(alert_result.scalars().all())
        sections["alerts"] = [
            {
                "id": str(a.id),
                "severity": a.severity,
                "title": a.title,
                "body": a.body,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ]

        # 7. Consent records
        consent_result = await db.execute(
            select(ConsentRecord).where(ConsentRecord.member_id.in_(member_ids))
        )
        consents = list(consent_result.scalars().all())
        sections["consent_records"] = [
            {
                "id": str(c.id),
                "consent_type": c.consent_type,
                "given_at": c.given_at.isoformat() if c.given_at else None,
                "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
            }
            for c in consents
        ]

        # 8. Spend records
        spend_result = await db.execute(
            select(SpendRecord).where(SpendRecord.member_id.in_(member_ids))
            .order_by(SpendRecord.period_start.desc())
        )
        spends = list(spend_result.scalars().all())
        sections["spend_records"] = [
            {
                "id": str(s.id),
                "amount": s.amount,
                "currency": s.currency,
                "model": s.model,
                "token_count": s.token_count,
                "period_start": s.period_start.isoformat() if s.period_start else None,
                "period_end": s.period_end.isoformat() if s.period_end else None,
            }
            for s in spends
        ]
    else:
        for key in ("capture_events", "risk_events", "alerts", "consent_records", "spend_records"):
            sections[key] = []

    # 9. Notification preferences
    pref_result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id
        )
    )
    prefs = list(pref_result.scalars().all())
    sections["notification_preferences"] = [
        {
            "id": str(p.id),
            "category": p.category,
            "channel": p.channel,
            "digest_mode": p.digest_mode,
            "enabled": p.enabled,
        }
        for p in prefs
    ]

    # Metadata
    sections["export_metadata"] = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user_id": str(user_id),
        "format": "JSON",
        "version": "1.0",
    }

    return sections


def _write_zip(user_id: UUID, data: dict) -> Path:
    """Write data to a ZIP file on disk."""
    exports_dir = _ensure_exports_dir()
    file_name = f"export_{user_id}_{uuid4().hex[:8]}.zip"
    file_path = exports_dir / file_name

    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for section_name, section_data in data.items():
            zf.writestr(f"{section_name}.json", _serialize(section_data))

    return file_path


def _write_zip_bytes(data: dict) -> bytes:
    """Write data to an in-memory ZIP and return bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for section_name, section_data in data.items():
            zf.writestr(f"{section_name}.json", _serialize(section_data))
    return buf.getvalue()
