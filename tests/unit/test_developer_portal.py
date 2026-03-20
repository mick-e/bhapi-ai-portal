"""Unit tests for developer portal."""

from uuid import uuid4

import pytest

from src.integrations.developer_portal import (
    create_developer_app,
    list_developer_apps,
)


@pytest.mark.asyncio
class TestDeveloperPortal:
    async def test_create_app(self, test_session):
        owner_id = uuid4()
        app, secret = await create_developer_app(test_session, owner_id, "My App")
        assert app.name == "My App"
        assert app.client_id.startswith("bhapi_")
        assert secret.startswith("bhapi_secret_")
        assert app.approved is False

    async def test_list_apps(self, test_session):
        owner_id = uuid4()
        await create_developer_app(test_session, owner_id, "App 1")
        await create_developer_app(test_session, owner_id, "App 2")
        apps = await list_developer_apps(test_session, owner_id)
        assert len(apps) == 2
