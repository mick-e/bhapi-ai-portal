"""API platform FastAPI router — OAuth 2.0 clients, tokens, usage."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_platform import schemas, service
from src.api_platform.oauth import (
    exchange_code_for_tokens,
    generate_authorization_code,
    refresh_access_token,
    revoke_token,
)
from src.auth.middleware import get_current_user
from src.database import get_db
from src.exceptions import ForbiddenError
from src.schemas import GroupContext

logger = structlog.get_logger()

router = APIRouter()


# ---------------------------------------------------------------------------
# Client management
# ---------------------------------------------------------------------------


@router.post("/clients", response_model=schemas.OAuthClientCreateResponse, status_code=201)
async def register_client(
    data: schemas.OAuthClientCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a new OAuth API client (pending admin approval)."""
    client, secret = await service.register_client(db, auth.user_id, data)
    await db.commit()

    response_data = schemas.OAuthClientResponse.model_validate(client)
    return schemas.OAuthClientCreateResponse(
        **response_data.model_dump(),
        client_secret=secret,
    )


@router.get("/clients", response_model=schemas.OAuthClientListResponse)
async def list_clients(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    all_clients: bool = Query(default=False, description="Admin: list all clients"),
):
    """List OAuth clients. Admins can list all; others see their own."""
    is_admin = auth.role in ("admin", "owner") or "admin" in (auth.permissions or [])
    owner_filter = None if (all_clients and is_admin) else auth.user_id

    clients, total = await service.list_clients(
        db, owner_id=owner_filter, offset=offset, limit=limit,
    )
    return schemas.OAuthClientListResponse(
        items=[schemas.OAuthClientResponse.model_validate(c) for c in clients],
        total=total,
    )


@router.get("/clients/{client_db_id}", response_model=schemas.OAuthClientResponse)
async def get_client(
    client_db_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get OAuth client details."""
    client = await service.get_client(db, client_db_id)
    is_admin = auth.role in ("admin", "owner") or "admin" in (auth.permissions or [])
    if client.owner_id != auth.user_id and not is_admin:
        raise ForbiddenError("Access denied to this client")
    return schemas.OAuthClientResponse.model_validate(client)


@router.post("/clients/{client_db_id}/approve", response_model=schemas.OAuthClientResponse)
async def approve_client(
    client_db_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: approve an OAuth client."""
    is_admin = auth.role in ("admin", "owner") or "admin" in (auth.permissions or [])
    if not is_admin:
        raise ForbiddenError("Admin access required to approve clients")

    client = await service.approve_client(db, client_db_id)
    await db.commit()
    return schemas.OAuthClientResponse.model_validate(client)


# ---------------------------------------------------------------------------
# OAuth 2.0 authorization flow
# ---------------------------------------------------------------------------


@router.post("/authorize", response_model=schemas.AuthorizationResponse, status_code=201)
async def authorize(
    data: schemas.AuthorizationRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """OAuth authorization endpoint — issues authorization code (PKCE required)."""
    # Validate client exists and is approved
    client = await service.get_client_by_client_id(db, data.client_id)
    if not client.is_approved:
        raise ForbiddenError("OAuth client is not approved")
    if not client.is_active:
        raise ForbiddenError("OAuth client is inactive")

    # Validate redirect_uri against registered URIs
    if client.redirect_uris:
        registered = client.redirect_uris if isinstance(client.redirect_uris, list) else []
        if registered and data.redirect_uri not in registered:
            raise ForbiddenError("redirect_uri is not registered for this client")

    scopes = [s.strip() for s in data.scope.split() if s.strip()]

    code = generate_authorization_code(
        client_id=data.client_id,
        user_id=auth.user_id,
        scopes=scopes,
        redirect_uri=data.redirect_uri,
        code_challenge=data.code_challenge,
        code_challenge_method=data.code_challenge_method,
    )

    logger.info(
        "oauth_authorize_issued",
        client_id=data.client_id,
        user_id=str(auth.user_id),
    )
    return schemas.AuthorizationResponse(code=code, state=data.state)


@router.post("/token", response_model=schemas.TokenResponse)
async def token_exchange(
    data: schemas.TokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """OAuth token exchange — authorization_code grant with PKCE."""
    access_token, refresh_token, scopes = await exchange_code_for_tokens(
        db=db,
        code=data.code,
        client_id_str=data.client_id,
        client_secret=data.client_secret,
        redirect_uri=data.redirect_uri,
        code_verifier=data.code_verifier,
    )
    await db.commit()

    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        scope=" ".join(scopes),
    )


@router.post("/token/refresh", response_model=schemas.TokenResponse)
async def token_refresh(
    data: schemas.TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """OAuth token refresh — issues new access + refresh token pair."""
    new_access, new_refresh, scopes = await refresh_access_token(
        db=db,
        refresh_token=data.refresh_token,
        client_id_str=data.client_id,
        client_secret=data.client_secret,
    )
    await db.commit()

    return schemas.TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        scope=" ".join(scopes),
    )


@router.post("/token/revoke", status_code=200)
async def token_revoke(
    data: schemas.TokenRevokeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Revoke an access or refresh token (RFC 7009)."""
    await revoke_token(
        db=db,
        token_str=data.token,
        client_id_str=data.client_id,
        client_secret=data.client_secret,
    )
    await db.commit()
    return {"revoked": True}


# ---------------------------------------------------------------------------
# Usage metrics
# ---------------------------------------------------------------------------


@router.get("/usage", response_model=schemas.UsageResponse)
async def get_usage(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client_db_id: UUID | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=90),
):
    """Get API usage metrics for caller's client (or a specified client for admins)."""
    is_admin = auth.role in ("admin", "owner") or "admin" in (auth.permissions or [])

    if client_db_id:
        if not is_admin:
            # Verify the caller owns this client
            client = await service.get_client(db, client_db_id)
            if client.owner_id != auth.user_id:
                raise ForbiddenError("Access denied to this client's usage data")
    else:
        # Get the caller's first client
        clients, _ = await service.list_clients(db, owner_id=auth.user_id, limit=1)
        if not clients:
            raise ForbiddenError("No API client registered for this account")
        client_db_id = clients[0].id

    return await service.get_usage(db, client_db_id, days=days)


# ---------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------


@router.get("/tiers", response_model=list[schemas.APIKeyTierResponse])
async def list_tiers(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List API tier configurations."""
    tiers = await service.list_tiers(db)
    return [schemas.APIKeyTierResponse.model_validate(t) for t in tiers]
