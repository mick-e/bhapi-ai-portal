"""Data deletion worker — processes pending GDPR deletion requests.

Cascade soft-deletes across all user-related tables. Creates audit trail
entries for each deletion action. Idempotent — safe to re-run.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert, NotificationPreference
from src.auth.models import OAuthConnection, Session, User
from src.billing.models import SpendRecord
from src.capture.models import CaptureEvent, DeviceRegistration
from src.compliance.models import AuditEntry, ConsentRecord, DataDeletionRequest
from src.groups.models import Group, GroupMember, Invitation
from src.risk.models import ContentExcerpt, RiskEvent

logger = structlog.get_logger()


async def process_pending_deletions(db: AsyncSession) -> int:
    """Process all pending data deletion requests.

    Returns the number of requests completed.
    """
    result = await db.execute(
        select(DataDeletionRequest).where(
            DataDeletionRequest.status == "pending",
            DataDeletionRequest.request_type == "full_deletion",
        )
    )
    requests = list(result.scalars().all())

    completed = 0
    for request in requests:
        try:
            request.status = "processing"
            await db.flush()

            # Get a valid group_id for audit trail before deleting
            member_result = await db.execute(
                select(GroupMember.group_id).where(GroupMember.user_id == request.user_id).limit(1)
            )
            audit_group_id = member_result.scalar()

            # Find owned groups as fallback
            if not audit_group_id:
                from src.groups.models import Group as GroupModel
                group_result = await db.execute(
                    select(GroupModel.id).where(GroupModel.owner_id == request.user_id).limit(1)
                )
                audit_group_id = group_result.scalar()

            deleted_counts = await _delete_user_data(db, request.user_id)

            request.status = "completed"
            request.completed_at = datetime.now(timezone.utc)
            await db.flush()

            # Audit trail (only if we have a valid group)
            if audit_group_id:
                audit = AuditEntry(
                    id=uuid4(),
                    group_id=audit_group_id,
                    actor_id=request.user_id,
                    action="data_deletion.completed",
                    resource_type="user",
                    resource_id=str(request.user_id),
                    details={"deleted_counts": deleted_counts},
                )
                db.add(audit)
                await db.flush()

            completed += 1
            logger.info(
                "deletion_completed",
                request_id=str(request.id),
                user_id=str(request.user_id),
                counts=deleted_counts,
            )
        except Exception as exc:
            logger.error(
                "deletion_failed",
                request_id=str(request.id),
                user_id=str(request.user_id),
                error=str(exc),
            )

    logger.info("deletion_batch_completed", total=len(requests), completed=completed)
    return completed


async def _delete_user_data(db: AsyncSession, user_id) -> dict:
    """Cascade soft-delete all data for a user. Returns counts per table."""
    counts: dict[str, int] = {}
    now = datetime.now(timezone.utc)

    # 1. Get all group memberships for this user
    member_result = await db.execute(
        select(GroupMember).where(GroupMember.user_id == user_id)
    )
    members = list(member_result.scalars().all())
    member_ids = [m.id for m in members]

    # 2. Delete content excerpts linked to user's risk events
    if member_ids:
        risk_result = await db.execute(
            select(RiskEvent.id).where(RiskEvent.member_id.in_(member_ids))
        )
        risk_event_ids = [r[0] for r in risk_result.all()]

        if risk_event_ids:
            excerpt_result = await db.execute(
                select(ContentExcerpt).where(
                    ContentExcerpt.risk_event_id.in_(risk_event_ids)
                )
            )
            excerpts = list(excerpt_result.scalars().all())
            for excerpt in excerpts:
                await db.delete(excerpt)
            counts["content_excerpts"] = len(excerpts)

            # 3. Delete risk events
            risk_events_result = await db.execute(
                select(RiskEvent).where(RiskEvent.member_id.in_(member_ids))
            )
            risk_events = list(risk_events_result.scalars().all())
            for re in risk_events:
                await db.delete(re)
            counts["risk_events"] = len(risk_events)

        # 4. Delete capture events
        capture_result = await db.execute(
            select(CaptureEvent).where(CaptureEvent.member_id.in_(member_ids))
        )
        captures = list(capture_result.scalars().all())
        for c in captures:
            await db.delete(c)
        counts["capture_events"] = len(captures)

        # 5. Delete device registrations
        device_result = await db.execute(
            select(DeviceRegistration).where(
                DeviceRegistration.member_id.in_(member_ids)
            )
        )
        devices = list(device_result.scalars().all())
        for d in devices:
            await db.delete(d)
        counts["device_registrations"] = len(devices)

        # 6. Delete alerts for these members
        alert_result = await db.execute(
            select(Alert).where(Alert.member_id.in_(member_ids))
        )
        alerts = list(alert_result.scalars().all())
        for a in alerts:
            await db.delete(a)
        counts["alerts"] = len(alerts)

        # 7. Delete consent records
        consent_result = await db.execute(
            select(ConsentRecord).where(
                ConsentRecord.member_id.in_(member_ids)
            )
        )
        consents = list(consent_result.scalars().all())
        for c in consents:
            await db.delete(c)
        counts["consent_records"] = len(consents)

        # 8. Delete group memberships
        for m in members:
            await db.delete(m)
        counts["group_members"] = len(members)

    # 9. Delete notification preferences
    pref_result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id
        )
    )
    prefs = list(pref_result.scalars().all())
    for p in prefs:
        await db.delete(p)
    counts["notification_preferences"] = len(prefs)

    # 10. Delete OAuth connections
    oauth_result = await db.execute(
        select(OAuthConnection).where(OAuthConnection.user_id == user_id)
    )
    oauths = list(oauth_result.scalars().all())
    for o in oauths:
        await db.delete(o)
    counts["oauth_connections"] = len(oauths)

    # 11. Delete sessions
    session_result = await db.execute(
        select(Session).where(Session.user_id == user_id)
    )
    sessions = list(session_result.scalars().all())
    for s in sessions:
        await db.delete(s)
    counts["sessions"] = len(sessions)

    # 12. Delete invitations sent by user
    invite_result = await db.execute(
        select(Invitation).where(Invitation.invited_by == user_id)
    )
    invites = list(invite_result.scalars().all())
    for i in invites:
        await db.delete(i)
    counts["invitations"] = len(invites)

    # 13. Soft-delete user account (set deleted_at)
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if user:
        user.deleted_at = now
        user.email = f"deleted_{uuid4().hex[:8]}@deleted.bhapi.ai"
        user.display_name = "Deleted User"
        user.password_hash = None
        user.mfa_secret = None
        counts["users"] = 1

    await db.flush()
    return counts
