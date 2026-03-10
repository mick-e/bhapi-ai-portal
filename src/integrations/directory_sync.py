"""Directory sync for SSO providers (Google Workspace, Microsoft Entra)."""

from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.sso_models import SSOConfig
from src.integrations.sso_provisioner import auto_provision_member

logger = structlog.get_logger()

# API endpoints
GOOGLE_DIRECTORY_URL = "https://admin.googleapis.com/admin/directory/v1/users"
MICROSOFT_GRAPH_USERS_URL = "https://graph.microsoft.com/v1.0/users"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"


async def sync_google_directory(
    db: AsyncSession,
    sso_config: SSOConfig,
) -> dict:
    """Sync members from Google Admin SDK directory.

    Uses the Google Admin SDK Directory API to list users in the domain,
    then auto-provisions each one via the SSO provisioner.

    Returns a summary dict with counts (synced, created, deactivated, errors).
    """
    domain = sso_config.tenant_id  # Google Workspace domain
    if not domain:
        logger.warning("google_sync_no_domain", config_id=str(sso_config.id))
        return {"synced": 0, "created": 0, "deactivated": 0, "errors": 0}

    logger.info(
        "google_directory_sync_start",
        config_id=str(sso_config.id),
        domain=domain,
    )

    summary = {"synced": 0, "created": 0, "deactivated": 0, "errors": 0}

    try:
        # Retrieve service account access token from config
        from src.encryption import decrypt_credential

        access_token = None
        if sso_config.tenant_id:
            # In production, exchange service account credentials for token
            # For now, we look for an access_token in the SSO config settings
            pass

        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"domain": domain, "maxResults": 500}
            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            response = await client.get(
                GOOGLE_DIRECTORY_URL,
                params=params,
                headers=headers,
            )

            if response.status_code != 200:
                logger.error(
                    "google_directory_api_error",
                    status=response.status_code,
                    config_id=str(sso_config.id),
                )
                summary["errors"] += 1
                return summary

            data = response.json()
            users = data.get("users", [])

            for google_user in users:
                try:
                    email = google_user.get("primaryEmail", "")
                    if not email:
                        continue

                    full_name = google_user.get("name", {})
                    display_name = full_name.get("fullName", email.split("@")[0])
                    external_id = google_user.get("id", "")

                    sso_user_info = {
                        "email": email,
                        "display_name": display_name,
                        "external_id": external_id,
                    }

                    member = await auto_provision_member(
                        db, sso_config.group_id, sso_user_info
                    )

                    if member is not None:
                        summary["created"] += 1
                    summary["synced"] += 1

                except Exception as exc:
                    logger.error(
                        "google_sync_user_error",
                        email=google_user.get("primaryEmail", "unknown"),
                        error=str(exc),
                    )
                    summary["errors"] += 1

    except httpx.HTTPError as exc:
        logger.error(
            "google_directory_http_error",
            config_id=str(sso_config.id),
            error=str(exc),
        )
        summary["errors"] += 1

    logger.info(
        "google_directory_sync_complete",
        config_id=str(sso_config.id),
        **summary,
    )
    return summary


async def sync_entra_directory(
    db: AsyncSession,
    sso_config: SSOConfig,
) -> dict:
    """Sync members from Microsoft Entra (Azure AD) via Graph API.

    Uses the Microsoft Graph API to list users in the tenant,
    then auto-provisions each one via the SSO provisioner.

    Returns a summary dict with counts (synced, created, deactivated, errors).
    """
    tenant_id = sso_config.tenant_id  # Microsoft tenant ID
    if not tenant_id:
        logger.warning("entra_sync_no_tenant", config_id=str(sso_config.id))
        return {"synced": 0, "created": 0, "deactivated": 0, "errors": 0}

    logger.info(
        "entra_directory_sync_start",
        config_id=str(sso_config.id),
        tenant_id=tenant_id,
    )

    summary = {"synced": 0, "created": 0, "deactivated": 0, "errors": 0}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Obtain access token via client credentials flow
            token_url = MICROSOFT_TOKEN_URL.format(tenant_id=tenant_id)
            token_response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "scope": "https://graph.microsoft.com/.default",
                    "client_id": "",  # Populated from env/config in production
                    "client_secret": "",  # Populated from env/config in production
                },
            )

            if token_response.status_code != 200:
                logger.error(
                    "entra_token_error",
                    status=token_response.status_code,
                    config_id=str(sso_config.id),
                )
                summary["errors"] += 1
                return summary

            access_token = token_response.json().get("access_token", "")

            # Step 2: List users from Microsoft Graph
            response = await client.get(
                MICROSOFT_GRAPH_USERS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"$select": "id,displayName,mail,userPrincipalName"},
            )

            if response.status_code != 200:
                logger.error(
                    "entra_directory_api_error",
                    status=response.status_code,
                    config_id=str(sso_config.id),
                )
                summary["errors"] += 1
                return summary

            data = response.json()
            users = data.get("value", [])

            for entra_user in users:
                try:
                    email = entra_user.get("mail") or entra_user.get(
                        "userPrincipalName", ""
                    )
                    if not email:
                        continue

                    display_name = entra_user.get("displayName", email.split("@")[0])
                    external_id = entra_user.get("id", "")

                    sso_user_info = {
                        "email": email,
                        "display_name": display_name,
                        "external_id": external_id,
                    }

                    member = await auto_provision_member(
                        db, sso_config.group_id, sso_user_info
                    )

                    if member is not None:
                        summary["created"] += 1
                    summary["synced"] += 1

                except Exception as exc:
                    logger.error(
                        "entra_sync_user_error",
                        email=entra_user.get("mail", "unknown"),
                        error=str(exc),
                    )
                    summary["errors"] += 1

    except httpx.HTTPError as exc:
        logger.error(
            "entra_directory_http_error",
            config_id=str(sso_config.id),
            error=str(exc),
        )
        summary["errors"] += 1

    logger.info(
        "entra_directory_sync_complete",
        config_id=str(sso_config.id),
        **summary,
    )
    return summary


async def run_directory_sync(db: AsyncSession) -> dict:
    """Run directory sync for all SSO configs with auto_provision enabled.

    Called by the background job runner on a schedule.
    Returns an aggregate summary across all configs.
    """
    result = await db.execute(
        select(SSOConfig).where(SSOConfig.auto_provision_members.is_(True))
    )
    configs = list(result.scalars().all())

    total_summary = {
        "configs_processed": 0,
        "synced": 0,
        "created": 0,
        "deactivated": 0,
        "errors": 0,
    }

    for config in configs:
        try:
            if config.provider == "google_workspace":
                summary = await sync_google_directory(db, config)
            elif config.provider == "microsoft_entra":
                summary = await sync_entra_directory(db, config)
            else:
                logger.warning(
                    "directory_sync_unsupported_provider",
                    provider=config.provider,
                    config_id=str(config.id),
                )
                continue

            total_summary["configs_processed"] += 1
            total_summary["synced"] += summary.get("synced", 0)
            total_summary["created"] += summary.get("created", 0)
            total_summary["deactivated"] += summary.get("deactivated", 0)
            total_summary["errors"] += summary.get("errors", 0)

        except Exception as exc:
            logger.error(
                "directory_sync_failed",
                config_id=str(config.id),
                provider=config.provider,
                error=str(exc),
            )
            total_summary["errors"] += 1

    logger.info("directory_sync_run_complete", **total_summary)
    return total_summary
