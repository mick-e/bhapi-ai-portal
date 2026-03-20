"""Unit tests for directory sync — mock API responses for Google and Entra."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from src.integrations.directory_sync import (
    run_directory_sync,
    sync_entra_directory,
    sync_google_directory,
)
from src.integrations.sso_models import SSOConfig
from tests.conftest import make_test_group


def _make_google_response(users: list[dict]) -> dict:
    """Build a mock Google Admin SDK directory response."""
    return {
        "kind": "admin#directory#users",
        "users": [
            {
                "id": u.get("id", str(uuid4())),
                "primaryEmail": u["email"],
                "name": {
                    "fullName": u.get("display_name", u["email"].split("@")[0]),
                    "givenName": u.get("given_name", ""),
                    "familyName": u.get("family_name", ""),
                },
            }
            for u in users
        ],
    }


def _make_entra_response(users: list[dict]) -> dict:
    """Build a mock Microsoft Graph users response."""
    return {
        "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users",
        "value": [
            {
                "id": u.get("id", str(uuid4())),
                "displayName": u.get("display_name", u["email"].split("@")[0]),
                "mail": u["email"],
                "userPrincipalName": u.get("upn", u["email"]),
            }
            for u in users
        ],
    }


@pytest.mark.asyncio
async def test_sync_google_directory_maps_users(test_session):
    """Google directory sync should map API users and call auto_provision."""
    group, owner_id = await make_test_group(
        test_session, name="Google School", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="google_workspace",
        tenant_id="gschool.com",
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    google_users = [
        {"email": "alice@gschool.com", "display_name": "Alice Smith"},
        {"email": "bob@gschool.com", "display_name": "Bob Jones"},
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = _make_google_response(google_users)

    with patch("src.integrations.directory_sync.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        summary = await sync_google_directory(test_session, sso)

    assert summary["synced"] == 2
    assert summary["errors"] == 0


@pytest.mark.asyncio
async def test_sync_google_directory_handles_api_error(test_session):
    """Google directory sync should handle non-200 responses gracefully."""
    group, owner_id = await make_test_group(
        test_session, name="Error School", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="google_workspace",
        tenant_id="error-school.com",
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {"error": "Forbidden"}

    with patch("src.integrations.directory_sync.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        summary = await sync_google_directory(test_session, sso)

    assert summary["synced"] == 0
    assert summary["errors"] == 1


@pytest.mark.asyncio
async def test_sync_google_directory_no_domain(test_session):
    """Google sync should return zeros when no domain/tenant_id configured."""
    group, owner_id = await make_test_group(
        test_session, name="No Domain", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="google_workspace",
        tenant_id=None,
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    summary = await sync_google_directory(test_session, sso)

    assert summary["synced"] == 0
    assert summary["created"] == 0
    assert summary["errors"] == 0


@pytest.mark.asyncio
async def test_sync_entra_directory_maps_users(test_session):
    """Entra directory sync should map Microsoft Graph users and provision."""
    group, owner_id = await make_test_group(
        test_session, name="Entra School", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="microsoft_entra",
        tenant_id="tenant-abc-123",
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    entra_users = [
        {"email": "carol@entra-school.com", "display_name": "Carol Davis"},
        {"email": "dave@entra-school.com", "display_name": "Dave Wilson"},
        {"email": "eve@entra-school.com", "display_name": "Eve Brown"},
    ]

    token_response = MagicMock()
    token_response.status_code = 200
    token_response.json.return_value = {"access_token": "mock-token"}

    users_response = MagicMock()
    users_response.status_code = 200
    users_response.json.return_value = _make_entra_response(entra_users)

    with patch("src.integrations.directory_sync.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=token_response)
        mock_client.get = AsyncMock(return_value=users_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        summary = await sync_entra_directory(test_session, sso)

    assert summary["synced"] == 3
    assert summary["errors"] == 0


@pytest.mark.asyncio
async def test_sync_entra_directory_token_failure(test_session):
    """Entra sync should handle token acquisition failure gracefully."""
    group, owner_id = await make_test_group(
        test_session, name="Token Fail", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="microsoft_entra",
        tenant_id="tenant-fail",
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    token_response = MagicMock()
    token_response.status_code = 401
    token_response.json.return_value = {"error": "invalid_client"}

    with patch("src.integrations.directory_sync.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=token_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        summary = await sync_entra_directory(test_session, sso)

    assert summary["synced"] == 0
    assert summary["errors"] == 1


@pytest.mark.asyncio
async def test_sync_entra_directory_no_tenant(test_session):
    """Entra sync should return zeros when no tenant_id configured."""
    group, owner_id = await make_test_group(
        test_session, name="No Tenant", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="microsoft_entra",
        tenant_id=None,
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    summary = await sync_entra_directory(test_session, sso)

    assert summary["synced"] == 0
    assert summary["created"] == 0
    assert summary["errors"] == 0


@pytest.mark.asyncio
async def test_run_directory_sync_processes_all_configs(test_session):
    """run_directory_sync should process all enabled SSO configs."""
    group1, _ = await make_test_group(
        test_session, name="School 1", group_type="school"
    )
    group2, _ = await make_test_group(
        test_session, name="School 2", group_type="school"
    )

    sso1 = SSOConfig(
        id=uuid4(),
        group_id=group1.id,
        provider="google_workspace",
        tenant_id="school1.com",
        auto_provision_members=True,
    )
    sso2 = SSOConfig(
        id=uuid4(),
        group_id=group2.id,
        provider="microsoft_entra",
        tenant_id="tenant-school2",
        auto_provision_members=True,
    )
    test_session.add_all([sso1, sso2])
    await test_session.flush()

    # Mock both sync functions to return known summaries
    with (
        patch(
            "src.integrations.directory_sync.sync_google_directory",
            new_callable=AsyncMock,
            return_value={"synced": 3, "created": 2, "deactivated": 0, "errors": 0},
        ),
        patch(
            "src.integrations.directory_sync.sync_entra_directory",
            new_callable=AsyncMock,
            return_value={"synced": 5, "created": 4, "deactivated": 1, "errors": 0},
        ),
    ):
        result = await run_directory_sync(test_session)

    assert result["configs_processed"] == 2
    assert result["synced"] == 8
    assert result["created"] == 6
    assert result["deactivated"] == 1
    assert result["errors"] == 0


@pytest.mark.asyncio
async def test_run_directory_sync_skips_disabled_configs(test_session):
    """run_directory_sync should only process configs with auto_provision enabled."""
    group, _ = await make_test_group(
        test_session, name="Disabled School", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="google_workspace",
        tenant_id="disabled.com",
        auto_provision_members=False,
    )
    test_session.add(sso)
    await test_session.flush()

    result = await run_directory_sync(test_session)

    assert result["configs_processed"] == 0
    assert result["synced"] == 0


@pytest.mark.asyncio
async def test_run_directory_sync_skips_unsupported_provider(test_session):
    """run_directory_sync should skip unsupported providers without crashing."""
    group, _ = await make_test_group(
        test_session, name="Unknown Provider", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="okta",
        tenant_id="okta-tenant",
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    result = await run_directory_sync(test_session)

    assert result["configs_processed"] == 0
    assert result["errors"] == 0


@pytest.mark.asyncio
async def test_sync_google_handles_http_exception(test_session):
    """Google sync should handle httpx connection errors."""
    group, owner_id = await make_test_group(
        test_session, name="HTTP Error", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="google_workspace",
        tenant_id="httperr.com",
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    with patch("src.integrations.directory_sync.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        summary = await sync_google_directory(test_session, sso)

    assert summary["errors"] >= 1
    assert summary["synced"] == 0
