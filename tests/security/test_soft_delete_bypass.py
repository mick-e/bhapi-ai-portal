"""Soft-delete bypass security tests.

Verifies that soft-deleted users and groups are properly filtered.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


@pytest.fixture
async def sec_client():
    """Security test client with committing session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    app = create_app()

    async def get_db_override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, session

    await session.close()
    await engine.dispose()


@pytest.mark.asyncio
async def test_soft_deleted_user_cannot_login(sec_client):
    """Soft-deleted user must not be able to log in."""
    client, session = sec_client

    email = "deleted-user@example.com"
    # Register
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Delete Me",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Soft-delete via account deletion endpoint
    resp = await client.delete("/api/v1/auth/account", headers=headers)
    assert resp.status_code == 204

    # Attempt login
    login = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "SecurePass1",
    })
    # Should be 401 — soft-deleted user filtered out by ORM auto-filter
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_soft_deleted_group_not_visible(sec_client):
    """Soft-deleted groups must not appear in group listings."""
    client, session = sec_client

    # Register user (auto-creates a group)
    reg = await client.post("/api/v1/auth/register", json={
        "email": "group-delete@example.com",
        "password": "SecurePass1",
        "display_name": "Group Deleter",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # List groups — should see the auto-created group
    groups_before = await client.get("/api/v1/groups", headers=headers)
    assert groups_before.status_code == 200
    initial_count = len(groups_before.json())
    assert initial_count >= 1

    # Create an additional group
    create_resp = await client.post("/api/v1/groups", json={
        "name": "Temporary Group",
        "type": "family",
    }, headers=headers)
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    # Soft-delete the new group directly via DB
    from uuid import UUID

    from sqlalchemy import select

    from src.groups.models import Group

    result = await session.execute(
        select(Group).where(Group.id == UUID(group_id))
    )
    group = result.scalar_one()
    group.soft_delete()
    await session.commit()

    # List groups — soft-deleted group should not appear
    groups_after = await client.get("/api/v1/groups", headers=headers)
    assert groups_after.status_code == 200
    group_ids = [g["id"] for g in groups_after.json()]
    assert group_id not in group_ids
