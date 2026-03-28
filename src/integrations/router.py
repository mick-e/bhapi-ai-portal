"""SIS integration and SSO configuration endpoints."""

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription
from src.encryption import decrypt_credential, encrypt_credential
from src.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from src.integrations.models import SISConnection
from src.integrations.schemas import SISConnectionResponse, SISConnectRequest, SISSyncResponse
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
    created_at: datetime

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


# ─── Yoti Webhook Callback (PUBLIC — no auth required) ─────────────────────


class YotiCallbackRequest(BaseModel):
    """Yoti webhook callback payload."""

    session_id: str = Field(..., description="Yoti verification session ID")
    status: str = Field(..., pattern="^(DONE|FAILED)$", description="Verification result status")
    score: float | None = Field(None, ge=0.0, le=1.0, description="Verification confidence score")


@router.post("/yoti/callback")
async def yoti_webhook_callback(
    data: YotiCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Process Yoti verification webhook callback (PUBLIC — called by Yoti, no auth)."""
    from src.integrations.yoti import handle_yoti_callback

    return await handle_yoti_callback(db, data.session_id, data.status, data.score)


# ─── Cross-Product ──────────────────────────────────────────────────────────


@router.post("/cross-product/register", status_code=201)
async def register_product(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a product for cross-product communication."""
    import hashlib

    from src.dependencies import resolve_group_id as _gid
    from src.integrations.cross_product import register_product as _register

    gid = _gid(None, auth)
    api_key = data.get("api_key", "")
    reg = await _register(
        db, product_name=data.get("product_name", ""),
        product_type=data.get("product_type", ""),
        api_key_hash=hashlib.sha256(api_key.encode()).hexdigest(),
        owner_group_id=gid,
        permissions=data.get("permissions"),
    )
    return {"id": str(reg.id), "product_name": reg.product_name, "active": reg.active}


@router.get("/cross-product/alerts")
async def list_xp_alerts(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List cross-product alerts."""
    from src.dependencies import resolve_group_id as _gid
    from src.integrations.cross_product import list_cross_product_alerts

    gid = _gid(None, auth)
    alerts = await list_cross_product_alerts(db, gid)
    return {"alerts": [
        {"id": str(a.id), "source_product": a.source_product, "alert_type": a.alert_type,
         "severity": a.severity, "title": a.title, "acknowledged": a.acknowledged}
        for a in alerts
    ]}


# ─── Developer Portal ──────────────────────────────────────────────────────


@router.post("/developer/apps", status_code=201)
async def create_developer_app(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a developer application."""
    from src.integrations.developer_portal import create_developer_app as _create

    app, secret = await _create(
        db, owner_id=auth.user_id, name=data.get("name", ""),
        description=data.get("description"),
        redirect_uris=data.get("redirect_uris"),
        scopes=data.get("scopes"),
    )
    return {"id": str(app.id), "client_id": app.client_id, "client_secret": secret, "name": app.name}


@router.get("/developer/apps")
async def list_developer_apps(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List developer applications."""
    from src.integrations.developer_portal import list_developer_apps as _list

    apps = await _list(db, auth.user_id)
    return {"apps": [
        {"id": str(a.id), "name": a.name, "client_id": a.client_id, "active": a.active, "approved": a.approved}
        for a in apps
    ]}


# ─── Marketplace ────────────────────────────────────────────────────────────


@router.get("/marketplace/modules")
async def list_modules(
    category: str | None = Query(None),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List marketplace modules."""
    from src.integrations.developer_portal import list_marketplace_modules

    modules = await list_marketplace_modules(db, category=category)
    return {"modules": [
        {"id": str(m.id), "name": m.name, "slug": m.slug, "category": m.category,
         "version": m.version, "install_count": m.install_count, "rating": m.rating}
        for m in modules
    ]}


@router.post("/marketplace/install", status_code=201)
async def install_module_endpoint(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Install a marketplace module."""
    from uuid import UUID as UUIDType

    from src.dependencies import resolve_group_id as _gid
    from src.integrations.developer_portal import install_module

    gid = _gid(None, auth)
    installed = await install_module(db, gid, UUIDType(data["module_id"]), config=data.get("config"))
    return {"id": str(installed.id), "active": installed.active}


# ─── Google Admin Console ────────────────────────────────────────────────────


class GoogleAdminSchoolRequest(BaseModel):
    school_id: str = Field(..., min_length=1)
    school_name: str = Field(..., min_length=1)
    admin_email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")


class GoogleAdminDeviceRequest(BaseModel):
    device_id: str = Field(..., min_length=1)
    serial_number: str | None = None
    os_version: str | None = None


class GoogleAdminDeviceStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(deployed|pending|error|unknown)$")


class GoogleAdminPolicyRequest(BaseModel):
    policy: dict = Field(..., min_length=1)


class GoogleAdminForceInstallRequest(BaseModel):
    extension_id: str = Field(..., min_length=1)


@router.post("/google-admin/schools", status_code=201)
async def register_google_admin_school(
    data: GoogleAdminSchoolRequest,
    auth: GroupContext = Depends(get_current_user),
):
    """Register a school for Google Admin extension deployment."""
    from src.integrations.google_admin import integration

    try:
        result = await integration.register_school(
            school_id=data.school_id,
            school_name=data.school_name,
            admin_email=data.admin_email,
        )
        return result
    except ValueError as e:
        raise ValidationError(str(e))


@router.get("/google-admin/schools/{school_id}/status")
async def get_google_admin_deployment_status(
    school_id: str,
    auth: GroupContext = Depends(get_current_user),
):
    """Get deployment status for a school."""
    from src.integrations.google_admin import integration

    status = await integration.get_deployment_status(school_id)
    if status is None:
        raise NotFoundError("School", school_id)
    return {
        "school_id": status.school_id,
        "total_devices": status.total_devices,
        "deployed": status.deployed,
        "pending": status.pending,
        "errors": status.errors,
        "deployment_percentage": status.deployment_percentage,
    }


@router.post("/google-admin/schools/{school_id}/devices", status_code=201)
async def add_google_admin_device(
    school_id: str,
    data: GoogleAdminDeviceRequest,
    auth: GroupContext = Depends(get_current_user),
):
    """Add a device to tracking for a school."""
    from src.integrations.google_admin import integration

    try:
        device = await integration.add_device(
            school_id=school_id,
            device_id=data.device_id,
            serial_number=data.serial_number,
            os_version=data.os_version,
        )
        return {
            "device_id": device.device_id,
            "status": device.status,
            "serial_number": device.serial_number,
            "os_version": device.os_version,
        }
    except KeyError:
        raise NotFoundError("School", school_id)
    except ValueError as e:
        raise ValidationError(str(e))


@router.patch("/google-admin/devices/{school_id}/{device_id}")
async def update_google_admin_device_status(
    school_id: str,
    device_id: str,
    data: GoogleAdminDeviceStatusUpdate,
    auth: GroupContext = Depends(get_current_user),
):
    """Update deployment status for a device."""
    from src.integrations.google_admin import integration

    try:
        device = await integration.update_device_status(
            school_id=school_id,
            device_id=device_id,
            status=data.status,
        )
    except ValueError as e:
        raise ValidationError(str(e))
    if device is None:
        raise NotFoundError("Device", device_id)
    return {
        "device_id": device.device_id,
        "status": device.status,
        "last_sync": device.last_sync.isoformat() if device.last_sync else None,
    }


@router.get("/google-admin/schools/{school_id}/devices")
async def list_google_admin_devices(
    school_id: str,
    status: str | None = Query(None),
    auth: GroupContext = Depends(get_current_user),
):
    """List devices for a school, optionally filtered by status."""
    from src.integrations.google_admin import integration

    try:
        devices = await integration.list_devices(school_id, status=status)
    except KeyError:
        raise NotFoundError("School", school_id)
    except ValueError as e:
        raise ValidationError(str(e))
    return {
        "devices": [
            {
                "device_id": d.device_id,
                "status": d.status,
                "last_sync": d.last_sync.isoformat() if d.last_sync else None,
                "os_version": d.os_version,
                "serial_number": d.serial_number,
            }
            for d in devices
        ],
    }


@router.post("/google-admin/schools/{school_id}/policy")
async def push_google_admin_policy(
    school_id: str,
    data: GoogleAdminPolicyRequest,
    auth: GroupContext = Depends(get_current_user),
):
    """Push a policy configuration to managed Chrome browsers."""
    from src.integrations.google_admin import integration

    try:
        result = await integration.push_policy(school_id, data.policy)
        return result
    except KeyError:
        raise NotFoundError("School", school_id)
    except ValueError as e:
        raise ValidationError(str(e))


@router.post("/google-admin/schools/{school_id}/force-install")
async def configure_google_admin_force_install(
    school_id: str,
    data: GoogleAdminForceInstallRequest,
    auth: GroupContext = Depends(get_current_user),
):
    """Configure force-install of the extension via admin console."""
    from src.integrations.google_admin import integration

    try:
        result = await integration.force_install_extension(school_id, data.extension_id)
        return result
    except KeyError:
        raise NotFoundError("School", school_id)
    except ValueError as e:
        raise ValidationError(str(e))
