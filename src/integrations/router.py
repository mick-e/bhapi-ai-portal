"""SIS integration and SSO configuration endpoints."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription
from src.encryption import decrypt_credential, encrypt_credential
from src.exceptions import ForbiddenError, NotFoundError, ConflictError, ValidationError
from src.integrations.models import SISConnection
from src.integrations.schemas import SISConnectRequest, SISConnectionResponse, SISSyncResponse
from src.integrations.sso_models import SSOConfig
from src.schemas import GroupContext

router = APIRouter(dependencies=[Depends(require_active_trial_or_subscription)])


async def _verify_group_access(auth: GroupContext, group_id: UUID, db) -> None:
    """Verify the authenticated user is a member of the specified group."""
    if auth.group_id == group_id:
        return
    from src.groups.models import GroupMember
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == auth.user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise ForbiddenError("You do not have access to this group")


@router.post("/connect", response_model=SISConnectionResponse, status_code=201)
async def connect_sis(
    data: SISConnectRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect a SIS provider (Clever, ClassLink, PowerSchool, or Canvas)."""
    await _verify_group_access(auth, data.group_id, db)
    from uuid import uuid4
    conn = SISConnection(
        id=uuid4(),
        group_id=data.group_id,
        provider=data.provider,
        credentials_encrypted=encrypt_credential(data.access_token),
        status="active",
        config_json=data.config,
    )
    db.add(conn)
    await db.flush()
    await db.refresh(conn)
    return conn


@router.post("/sync/{connection_id}", response_model=SISSyncResponse)
async def sync_sis(
    connection_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger roster sync for a SIS connection."""
    from datetime import datetime, timezone
    result = await db.execute(
        select(SISConnection).where(SISConnection.id == connection_id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise NotFoundError("SIS Connection", str(connection_id))
    await _verify_group_access(auth, conn.group_id, db)

    token = decrypt_credential(conn.credentials_encrypted)

    if conn.provider == "clever":
        from src.integrations.clever import fetch_clever_roster
        roster = await fetch_clever_roster(token)
    elif conn.provider == "classlink":
        from src.integrations.classlink import fetch_classlink_roster
        roster = await fetch_classlink_roster(token)
    elif conn.provider == "powerschool":
        from src.integrations.powerschool import fetch_powerschool_roster
        base_url = (conn.config_json or {}).get("base_url", "https://powerschool.example.com")
        roster = await fetch_powerschool_roster(token, base_url)
    elif conn.provider == "canvas":
        from src.integrations.canvas import fetch_canvas_roster
        base_url = (conn.config_json or {}).get("base_url", "https://canvas.instructure.com")
        course_id = (conn.config_json or {}).get("course_id", "")
        roster = await fetch_canvas_roster(token, base_url, course_id)
    else:
        raise ValidationError(f"Unsupported SIS provider: {conn.provider}")

    from src.integrations.sis_sync import sync_roster
    summary = await sync_roster(db, conn.group_id, roster)

    conn.last_synced = datetime.now(timezone.utc)
    await db.flush()

    return SISSyncResponse(connection_id=conn.id, **summary)


@router.get("/status", response_model=list[SISConnectionResponse])
async def list_connections(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List SIS connections for a group."""
    await _verify_group_access(auth, group_id, db)
    result = await db.execute(
        select(SISConnection).where(SISConnection.group_id == group_id)
    )
    return list(result.scalars().all())


@router.delete("/disconnect/{connection_id}")
async def disconnect_sis(
    connection_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect a SIS provider."""
    result = await db.execute(
        select(SISConnection).where(SISConnection.id == connection_id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise NotFoundError("SIS Connection", str(connection_id))
    await _verify_group_access(auth, conn.group_id, db)

    conn.status = "inactive"
    conn.credentials_encrypted = None
    await db.flush()
    return {"status": "disconnected", "connection_id": str(connection_id)}


@router.post("/age-verify/start")
async def start_age_verify(
    group_id: UUID = Query(...),
    member_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start age verification via Yoti."""
    await _verify_group_access(auth, group_id, db)
    from src.integrations.age_verification import start_age_verification
    return await start_age_verification(db, group_id, member_id)


# ─── SSO Configuration ────────────────────────────────────────────────────────


class SSOConfigRequest(BaseModel):
    group_id: UUID
    provider: str = Field(pattern="^(google_workspace|microsoft_entra)$")
    tenant_id: str | None = None
    auto_provision_members: bool = False


class SSOConfigResponse(BaseModel):
    id: UUID
    group_id: UUID
    provider: str
    tenant_id: str | None
    auto_provision_members: bool
    created_at: str

    model_config = {"from_attributes": True}


@router.post("/sso", response_model=SSOConfigResponse, status_code=201)
async def create_sso_config(
    data: SSOConfigRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create SSO configuration for a group."""
    await _verify_group_access(auth, data.group_id, db)
    # Check for existing config with same provider
    result = await db.execute(
        select(SSOConfig).where(
            SSOConfig.group_id == data.group_id,
            SSOConfig.provider == data.provider,
        )
    )
    if result.scalar_one_or_none():
        raise ConflictError(f"SSO config for {data.provider} already exists for this group")

    config = SSOConfig(
        id=uuid4(),
        group_id=data.group_id,
        provider=data.provider,
        tenant_id=data.tenant_id,
        auto_provision_members=data.auto_provision_members,
    )
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return config


@router.get("/sso", response_model=list[SSOConfigResponse])
async def list_sso_configs(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List SSO configurations for a group."""
    await _verify_group_access(auth, group_id, db)
    result = await db.execute(
        select(SSOConfig).where(SSOConfig.group_id == group_id)
    )
    return list(result.scalars().all())


@router.patch("/sso/{config_id}", response_model=SSOConfigResponse)
async def update_sso_config(
    config_id: UUID,
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an SSO configuration."""
    result = await db.execute(
        select(SSOConfig).where(SSOConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise NotFoundError("SSO Config", str(config_id))
    await _verify_group_access(auth, config.group_id, db)

    if "tenant_id" in data:
        config.tenant_id = data["tenant_id"]
    if "auto_provision_members" in data:
        config.auto_provision_members = data["auto_provision_members"]
    await db.flush()
    await db.refresh(config)
    return config


@router.delete("/sso/{config_id}")
async def delete_sso_config(
    config_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an SSO configuration."""
    result = await db.execute(
        select(SSOConfig).where(SSOConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise NotFoundError("SSO Config", str(config_id))
    await _verify_group_access(auth, config.group_id, db)

    await db.delete(config)
    await db.flush()
    return {"status": "deleted", "config_id": str(config_id)}


@router.post("/sso/{config_id}/sync")
async def trigger_directory_sync(
    config_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger directory sync for an SSO config."""
    result = await db.execute(
        select(SSOConfig).where(SSOConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise NotFoundError("SSO Config", str(config_id))
    await _verify_group_access(auth, config.group_id, db)

    from src.integrations.directory_sync import (
        sync_entra_directory,
        sync_google_directory,
    )

    if config.provider == "google_workspace":
        summary = await sync_google_directory(db, config.id)
    elif config.provider == "microsoft_entra":
        summary = await sync_entra_directory(db, config.id)
    else:
        raise ValidationError(f"Directory sync not supported for provider: {config.provider}")

    return summary


@router.post("/age-verify/callback")
async def age_verify_callback(
    group_id: UUID = Query(...),
    member_id: UUID = Query(...),
    session_id: str = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Process age verification result callback."""
    await _verify_group_access(auth, group_id, db)
    from src.integrations.age_verification import process_age_verification_result
    return await process_age_verification_result(db, group_id, member_id, session_id)
