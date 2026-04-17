"""FERPA compliance module API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import get_current_user
from src.database import get_db
from src.exceptions import ForbiddenError
from src.ferpa.schemas import (
    AccessLogCreate,
    AccessLogResponse,
    AnnualNotificationCreate,
    AnnualNotificationResponse,
    DataSharingAgreementCreate,
    DataSharingAgreementResponse,
    EducationalRecordCreate,
    EducationalRecordResponse,
)
from src.ferpa.service import (
    create_data_sharing_agreement,
    create_educational_record,
    list_access_logs,
    list_data_sharing_agreements,
    list_educational_records,
    log_access,
    send_annual_notification,
)
from src.schemas import GroupContext

router = APIRouter()


# ---------------------------------------------------------------------------
# School-account guard
# ---------------------------------------------------------------------------


async def _require_school_account(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupContext:
    """Ensure the authenticated user has a school account.

    FERPA endpoints are restricted to school administrators.
    GroupContext does not carry account_type, so we query the User model.
    """
    from src.auth.models import User

    result = await db.execute(select(User).where(User.id == auth.user_id))
    user = result.scalar_one_or_none()
    if not user or user.account_type != "school":
        raise ForbiddenError("FERPA endpoints require a school account")
    return auth


SchoolAuth = Depends(_require_school_account)


# ---------------------------------------------------------------------------
# Educational Records
# ---------------------------------------------------------------------------


@router.post(
    "/records",
    response_model=EducationalRecordResponse,
    status_code=201,
)
async def create_record(
    payload: EducationalRecordCreate,
    auth: GroupContext = SchoolAuth,
    db: AsyncSession = Depends(get_db),
):
    """Create a FERPA educational record designation."""
    record = await create_educational_record(
        db=db,
        group_id=auth.group_id,
        user_id=auth.user_id,
        member_id=payload.member_id,
        record_type=payload.record_type,
        title=payload.title,
        description=payload.description,
        is_directory_info=payload.is_directory_info,
        classification=payload.classification,
        metadata_json=payload.metadata_json,
    )
    return record


@router.get("/records", response_model=list[EducationalRecordResponse])
async def get_records(
    auth: GroupContext = SchoolAuth,
    db: AsyncSession = Depends(get_db),
):
    """List all FERPA educational records for the school."""
    return await list_educational_records(db=db, group_id=auth.group_id)


# ---------------------------------------------------------------------------
# Access Logs
# ---------------------------------------------------------------------------


@router.post(
    "/access-log",
    response_model=AccessLogResponse,
    status_code=201,
)
async def create_access_log(
    payload: AccessLogCreate,
    auth: GroupContext = SchoolAuth,
    db: AsyncSession = Depends(get_db),
):
    """Log access to a FERPA educational record (34 CFR 99.32)."""
    entry = await log_access(
        db=db,
        group_id=auth.group_id,
        accessor_user_id=auth.user_id,
        record_id=payload.record_id,
        access_type=payload.access_type,
        purpose=payload.purpose,
        legitimate_interest=payload.legitimate_interest,
    )
    return entry


@router.get("/access-log", response_model=list[AccessLogResponse])
async def get_access_logs(
    member_id: UUID | None = Query(default=None),
    auth: GroupContext = SchoolAuth,
    db: AsyncSession = Depends(get_db),
):
    """List FERPA access logs, optionally filtered by member."""
    return await list_access_logs(
        db=db, group_id=auth.group_id, member_id=member_id,
    )


# ---------------------------------------------------------------------------
# Data Sharing Agreements
# ---------------------------------------------------------------------------


@router.post(
    "/sharing-agreements",
    response_model=DataSharingAgreementResponse,
    status_code=201,
)
async def create_sharing_agreement(
    payload: DataSharingAgreementCreate,
    auth: GroupContext = SchoolAuth,
    db: AsyncSession = Depends(get_db),
):
    """Create a third-party data sharing agreement."""
    agreement = await create_data_sharing_agreement(
        db=db,
        group_id=auth.group_id,
        user_id=auth.user_id,
        third_party_name=payload.third_party_name,
        purpose=payload.purpose,
        data_elements=payload.data_elements,
        legal_basis=payload.legal_basis,
        effective_date=payload.effective_date,
        expiration_date=payload.expiration_date,
        terms=payload.terms,
    )
    return agreement


@router.get(
    "/sharing-agreements",
    response_model=list[DataSharingAgreementResponse],
)
async def get_sharing_agreements(
    auth: GroupContext = SchoolAuth,
    db: AsyncSession = Depends(get_db),
):
    """List all data sharing agreements for the school."""
    return await list_data_sharing_agreements(db=db, group_id=auth.group_id)


# ---------------------------------------------------------------------------
# Annual Notification
# ---------------------------------------------------------------------------


@router.post(
    "/annual-notification",
    response_model=AnnualNotificationResponse,
    status_code=201,
)
async def create_annual_notification(
    payload: AnnualNotificationCreate,
    auth: GroupContext = SchoolAuth,
    db: AsyncSession = Depends(get_db),
):
    """Send (record) an annual FERPA notification for a school year."""
    notification = await send_annual_notification(
        db=db,
        group_id=auth.group_id,
        school_year=payload.school_year,
        template_version=payload.template_version,
    )
    return notification
