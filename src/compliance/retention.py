"""Data retention policy engine (COPPA 2026).

Provides configurable retention per data type with automated deletion
and parent-facing disclosure. Registered as a background job.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.compliance.models import RetentionPolicy
from src.exceptions import ValidationError

logger = structlog.get_logger()

# Default retention policies applied when a group is created or
# when no custom policy exists.
DEFAULT_RETENTION_POLICIES = [
    {
        "data_type": "capture_events",
        "retention_days": 365,
        "description": "AI interaction capture events (prompts, responses, metadata)",
    },
    {
        "data_type": "risk_events",
        "retention_days": 365,
        "description": "Risk assessment events and safety classifications",
    },
    {
        "data_type": "content_excerpts",
        "retention_days": 365,
        "description": "Encrypted content excerpts from AI interactions",
    },
    {
        "data_type": "conversation_summaries",
        "retention_days": 365,
        "description": "AI-generated conversation summaries for parents",
    },
    {
        "data_type": "alerts",
        "retention_days": 730,
        "description": "Safety alerts and notification history",
    },
    {
        "data_type": "audit_entries",
        "retention_days": 1095,
        "description": "Compliance audit trail entries (3-year regulatory minimum)",
    },
]

VALID_DATA_TYPES = {p["data_type"] for p in DEFAULT_RETENTION_POLICIES}

# Minimum retention days per type (regulatory requirements)
MIN_RETENTION_DAYS = {
    "capture_events": 30,
    "risk_events": 90,
    "content_excerpts": 30,
    "conversation_summaries": 30,
    "alerts": 90,
    "audit_entries": 1095,  # 3 years for audit logs
}


async def get_retention_policies(db: AsyncSession, group_id: UUID) -> list[RetentionPolicy]:
    """Get all retention policies for a group, creating defaults if none exist."""
    result = await db.execute(
        select(RetentionPolicy).where(RetentionPolicy.group_id == group_id)
    )
    policies = list(result.scalars().all())

    if not policies:
        policies = await _create_default_policies(db, group_id)

    return policies


async def _create_default_policies(
    db: AsyncSession, group_id: UUID
) -> list[RetentionPolicy]:
    """Create default retention policies for a new group."""
    policies = []
    for default in DEFAULT_RETENTION_POLICIES:
        policy = RetentionPolicy(
            id=uuid4(),
            group_id=group_id,
            data_type=default["data_type"],
            retention_days=default["retention_days"],
            description=default["description"],
            auto_delete=True,
        )
        db.add(policy)
        policies.append(policy)
    await db.flush()
    return policies


async def update_retention_policy(
    db: AsyncSession,
    group_id: UUID,
    data_type: str,
    retention_days: int,
    auto_delete: bool = True,
) -> RetentionPolicy:
    """Update retention policy for a specific data type."""
    if data_type not in VALID_DATA_TYPES:
        raise ValidationError(f"Invalid data type. Must be one of: {', '.join(sorted(VALID_DATA_TYPES))}")

    min_days = MIN_RETENTION_DAYS.get(data_type, 30)
    if retention_days < min_days:
        raise ValidationError(
            f"Retention for {data_type} must be at least {min_days} days (regulatory minimum)"
        )

    result = await db.execute(
        select(RetentionPolicy).where(
            RetentionPolicy.group_id == group_id,
            RetentionPolicy.data_type == data_type,
        )
    )
    policy = result.scalar_one_or_none()

    if not policy:
        # Create the policy if it doesn't exist
        policy = RetentionPolicy(
            id=uuid4(),
            group_id=group_id,
            data_type=data_type,
            retention_days=retention_days,
            description=next(
                (p["description"] for p in DEFAULT_RETENTION_POLICIES if p["data_type"] == data_type),
                data_type,
            ),
            auto_delete=auto_delete,
        )
        db.add(policy)
    else:
        policy.retention_days = retention_days
        policy.auto_delete = auto_delete

    await db.flush()
    await db.refresh(policy)
    return policy


async def get_retention_disclosure(db: AsyncSession, group_id: UUID) -> dict:
    """Get parent-facing retention disclosure for a group.

    Returns a human-readable summary of what data is collected,
    how long it's kept, and when it will be automatically deleted.
    """
    policies = await get_retention_policies(db, group_id)

    disclosure = {
        "group_id": str(group_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policies": [],
        "summary": (
            "We retain your child's data only as long as necessary to provide "
            "our safety monitoring service. You can adjust retention periods "
            "below. Data is automatically and permanently deleted after the "
            "retention period expires."
        ),
    }

    for policy in policies:
        next_cleanup = None
        if policy.last_cleanup_at:
            next_cleanup = (policy.last_cleanup_at + timedelta(days=1)).isoformat()

        disclosure["policies"].append({
            "data_type": policy.data_type,
            "description": policy.description,
            "retention_days": policy.retention_days,
            "auto_delete": policy.auto_delete,
            "records_deleted_to_date": policy.records_deleted,
            "next_scheduled_cleanup": next_cleanup,
            "minimum_allowed_days": MIN_RETENTION_DAYS.get(policy.data_type, 30),
        })

    return disclosure


async def run_retention_cleanup(db: AsyncSession) -> dict:
    """Execute retention cleanup for all groups with auto_delete enabled.

    Called by the background job runner. Deletes records older than the
    configured retention period for each data type.
    """
    result = await db.execute(
        select(RetentionPolicy).where(RetentionPolicy.auto_delete.is_(True))
    )
    policies = list(result.scalars().all())

    total_deleted = 0
    groups_processed = set()
    errors = []

    for policy in policies:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
            deleted = await _delete_expired_records(db, policy, cutoff)

            policy.last_cleanup_at = datetime.now(timezone.utc)
            policy.records_deleted += deleted
            total_deleted += deleted
            groups_processed.add(policy.group_id)

            if deleted > 0:
                logger.info(
                    "retention_cleanup",
                    group_id=str(policy.group_id),
                    data_type=policy.data_type,
                    records_deleted=deleted,
                    cutoff=cutoff.isoformat(),
                )
        except Exception as exc:
            logger.error(
                "retention_cleanup_error",
                group_id=str(policy.group_id),
                data_type=policy.data_type,
                error=str(exc),
            )
            errors.append({"group_id": str(policy.group_id), "data_type": policy.data_type, "error": str(exc)})

    await db.flush()

    return {
        "groups_processed": len(groups_processed),
        "total_deleted": total_deleted,
        "errors": len(errors),
    }


async def _delete_expired_records(
    db: AsyncSession, policy: RetentionPolicy, cutoff: datetime
) -> int:
    """Delete records older than cutoff for the given data type and group."""
    table_map = {
        "capture_events": ("capture_events", "timestamp"),
        "risk_events": ("risk_events", "created_at"),
        "content_excerpts": ("content_excerpts", "created_at"),
        "conversation_summaries": ("conversation_summaries", "created_at"),
        "alerts": ("alerts", "created_at"),
        "audit_entries": ("audit_entries", "created_at"),
    }

    table_info = table_map.get(policy.data_type)
    if not table_info:
        return 0

    table_name, timestamp_col = table_info

    # Use raw SQL for cross-table deletion since we're referencing
    # tables from other modules. This avoids cross-module model imports.
    from sqlalchemy import text

    result = await db.execute(
        text(
            f"DELETE FROM {table_name} "
            f"WHERE group_id = :group_id AND {timestamp_col} < :cutoff"
        ),
        {"group_id": str(policy.group_id), "cutoff": cutoff},
    )
    return result.rowcount
