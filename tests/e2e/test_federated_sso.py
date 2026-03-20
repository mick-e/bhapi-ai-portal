"""E2E tests for federated SSO (Google Workspace / Microsoft Entra)."""

from uuid import uuid4

import pytest

from src.auth.oauth import PROVIDER_CONFIGS


def test_google_provider_configured():
    """Google OAuth provider should be configured."""
    assert "google" in PROVIDER_CONFIGS
    config = PROVIDER_CONFIGS["google"]
    assert "accounts.google.com" in config.authorize_url
    assert "googleapis.com" in config.token_url
    assert "openid" in config.scopes


def test_microsoft_provider_configured():
    """Microsoft OAuth provider should be configured."""
    assert "microsoft" in PROVIDER_CONFIGS
    config = PROVIDER_CONFIGS["microsoft"]
    assert "microsoftonline.com" in config.authorize_url
    assert "openid" in config.scopes


def test_apple_provider_configured():
    """Apple OAuth provider should be configured."""
    assert "apple" in PROVIDER_CONFIGS
    config = PROVIDER_CONFIGS["apple"]
    assert "apple.com" in config.authorize_url
    assert config.response_mode == "form_post"


def test_sso_config_model():
    """SSOConfig model should be importable and have expected fields."""
    from src.integrations.sso_models import SSOConfig
    assert hasattr(SSOConfig, "group_id")
    assert hasattr(SSOConfig, "provider")
    assert hasattr(SSOConfig, "tenant_id")
    assert hasattr(SSOConfig, "auto_provision_members")


@pytest.mark.asyncio
async def test_sso_config_creation(test_session):
    """Should be able to create SSO config for a group."""
    from src.integrations.sso_models import SSOConfig
    from tests.conftest import make_test_group

    group, owner_id = await make_test_group(test_session, name="School", group_type="school")

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="google_workspace",
        tenant_id="school.edu",
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    from sqlalchemy import select
    result = await test_session.execute(
        select(SSOConfig).where(SSOConfig.group_id == group.id)
    )
    config = result.scalar_one()
    assert config.provider == "google_workspace"
    assert config.tenant_id == "school.edu"
    assert config.auto_provision_members is True
