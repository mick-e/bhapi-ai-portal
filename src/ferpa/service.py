"""FERPA compliance module — business logic."""

from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ferpa.models import (
    AccessLog,
    AnnualNotification,
    DataSharingAgreement,
    EducationalRecord,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Educational Records
# ---------------------------------------------------------------------------


async def create_educational_record(
    db: AsyncSession,
    group_id: UUID,
    user_id: UUID,
    member_id: UUID,
    record_type: str,
    title: str,
    description: str | None = None,
    is_directory_info: bool = False,
    classification: str = "protected",
    metadata_json: dict | None = None,
) -> EducationalRecord:
    """Create a FERPA educational record designation."""
    record = EducationalRecord(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        record_type=record_type,
        title=title,
        description=description,
        is_directory_info=is_directory_info,
        classification=classification,
        created_by=user_id,
        metadata_json=metadata_json,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    logger.info(
        "ferpa_record_created",
        record_id=str(record.id),
        group_id=str(group_id),
        record_type=record_type,
    )
    return record


async def list_educational_records(
    db: AsyncSession,
    group_id: UUID,
) -> list[EducationalRecord]:
    """List all educational records for a group."""
    result = await db.execute(
        select(EducationalRecord)
        .where(EducationalRecord.group_id == group_id)
        .order_by(EducationalRecord.created_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Access Logs (34 CFR 99.32)
# ---------------------------------------------------------------------------


async def log_access(
    db: AsyncSession,
    group_id: UUID,
    accessor_user_id: UUID,
    record_id: UUID,
    access_type: str,
    purpose: str,
    legitimate_interest: str | None = None,
) -> AccessLog:
    """Log access to a FERPA educational record."""
    entry = AccessLog(
        id=uuid4(),
        group_id=group_id,
        record_id=record_id,
        accessor_user_id=accessor_user_id,
        access_type=access_type,
        purpose=purpose,
        legitimate_interest=legitimate_interest,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    logger.info(
        "ferpa_access_logged",
        log_id=str(entry.id),
        group_id=str(group_id),
        record_id=str(record_id),
        access_type=access_type,
    )
    return entry


async def list_access_logs(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID | None = None,
) -> list[AccessLog]:
    """List access logs for a group, optionally filtered by member."""
    stmt = (
        select(AccessLog)
        .where(AccessLog.group_id == group_id)
        .order_by(AccessLog.accessed_at.desc())
    )
    if member_id is not None:
        # Join through educational record to filter by member
        stmt = (
            select(AccessLog)
            .join(EducationalRecord, AccessLog.record_id == EducationalRecord.id)
            .where(AccessLog.group_id == group_id)
            .where(EducationalRecord.member_id == member_id)
            .order_by(AccessLog.accessed_at.desc())
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Data Sharing Agreements
# ---------------------------------------------------------------------------


async def create_data_sharing_agreement(
    db: AsyncSession,
    group_id: UUID,
    user_id: UUID,
    third_party_name: str,
    purpose: str,
    data_elements: dict,
    legal_basis: str,
    effective_date,
    expiration_date=None,
    terms: dict | None = None,
) -> DataSharingAgreement:
    """Create a FERPA data sharing agreement."""
    agreement = DataSharingAgreement(
        id=uuid4(),
        group_id=group_id,
        third_party_name=third_party_name,
        purpose=purpose,
        data_elements=data_elements,
        legal_basis=legal_basis,
        effective_date=effective_date,
        expiration_date=expiration_date,
        created_by=user_id,
        terms=terms,
    )
    db.add(agreement)
    await db.flush()
    await db.refresh(agreement)

    logger.info(
        "ferpa_sharing_agreement_created",
        agreement_id=str(agreement.id),
        group_id=str(group_id),
        third_party=third_party_name,
    )
    return agreement


async def list_data_sharing_agreements(
    db: AsyncSession,
    group_id: UUID,
) -> list[DataSharingAgreement]:
    """List all data sharing agreements for a group."""
    result = await db.execute(
        select(DataSharingAgreement)
        .where(DataSharingAgreement.group_id == group_id)
        .order_by(DataSharingAgreement.created_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Annual Notification
# ---------------------------------------------------------------------------


async def send_annual_notification(
    db: AsyncSession,
    group_id: UUID,
    school_year: str,
    template_version: int = 1,
) -> AnnualNotification:
    """Record an annual FERPA notification for a school year."""
    notification = AnnualNotification(
        id=uuid4(),
        group_id=group_id,
        school_year=school_year,
        template_version=template_version,
        recipient_count=0,
        notification_method="email",
    )
    db.add(notification)
    await db.flush()
    await db.refresh(notification)

    logger.info(
        "ferpa_annual_notification_sent",
        notification_id=str(notification.id),
        group_id=str(group_id),
        school_year=school_year,
    )
    return notification
