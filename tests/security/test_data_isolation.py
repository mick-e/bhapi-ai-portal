"""Data isolation security tests.

Verifies that users in different groups cannot access each other's data.
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
    """Security test client with committing sessions."""
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
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await session.close()
    await engine.dispose()


async def _register_and_login(client, email, password="SecurePass1", display_name="User"):
    """Register a user and return their auth headers."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "display_name": display_name,
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Cross-User Group Isolation ---

@pytest.mark.asyncio
async def test_user_cannot_list_other_groups(sec_client):
    """User A cannot see User B's groups."""
    h1 = await _register_and_login(sec_client, "alice@test.com", display_name="Alice")
    h2 = await _register_and_login(sec_client, "bob@test.com", display_name="Bob")

    # Alice creates a group
    await sec_client.post("/api/v1/groups", json={
        "name": "Alice Family", "type": "family",
    }, headers=h1)

    # Bob should only see his own auto-created group, not Alice's
    resp = await sec_client.get("/api/v1/groups", headers=h2)
    assert resp.status_code == 200
    groups = resp.json()
    assert all("Alice Family" != g["name"] for g in groups)


@pytest.mark.asyncio
async def test_user_cannot_access_other_group_by_id(sec_client):
    """User A cannot access User B's group by direct ID."""
    h1 = await _register_and_login(sec_client, "alice2@test.com", display_name="Alice2")
    h2 = await _register_and_login(sec_client, "bob2@test.com", display_name="Bob2")

    # Alice creates a group
    create_resp = await sec_client.post("/api/v1/groups", json={
        "name": "Alice Private", "type": "family",
    }, headers=h1)
    group_id = create_resp.json()["id"]

    # Bob tries to access Alice's group
    resp = await sec_client.get(f"/api/v1/groups/{group_id}", headers=h2)
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_user_cannot_invite_to_other_group(sec_client):
    """User A cannot invite members to User B's group."""
    h1 = await _register_and_login(sec_client, "alice3@test.com", display_name="Alice3")
    h2 = await _register_and_login(sec_client, "bob3@test.com", display_name="Bob3")

    # Alice creates a group
    create_resp = await sec_client.post("/api/v1/groups", json={
        "name": "Alice Only", "type": "family",
    }, headers=h1)
    group_id = create_resp.json()["id"]

    # Bob tries to invite someone to Alice's group
    resp = await sec_client.post(f"/api/v1/groups/{group_id}/invite", json={
        "email": "victim@test.com",
        "role": "member",
    }, headers=h2)
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_user_cannot_delete_other_group(sec_client):
    """User A cannot delete User B's group."""
    h1 = await _register_and_login(sec_client, "alice4@test.com", display_name="Alice4")
    h2 = await _register_and_login(sec_client, "bob4@test.com", display_name="Bob4")

    create_resp = await sec_client.post("/api/v1/groups", json={
        "name": "Alice Protected", "type": "family",
    }, headers=h1)
    group_id = create_resp.json()["id"]

    # Bob tries to delete Alice's group
    resp = await sec_client.delete(f"/api/v1/groups/{group_id}", headers=h2)
    assert resp.status_code in (403, 404)

    # Alice's group should still exist
    resp = await sec_client.get(f"/api/v1/groups/{group_id}", headers=h1)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_member_cannot_add_members(sec_client):
    """Non-admin member cannot invite others."""
    h1 = await _register_and_login(sec_client, "admin5@test.com", display_name="Admin5")
    h2 = await _register_and_login(sec_client, "member5@test.com", display_name="Member5")

    # Admin creates a group
    create_resp = await sec_client.post("/api/v1/groups", json={
        "name": "Admin Group", "type": "family",
    }, headers=h1)
    group_id = create_resp.json()["id"]

    # Admin invites Member
    invite_resp = await sec_client.post(f"/api/v1/groups/{group_id}/invite", json={
        "email": "member5@test.com",
        "role": "member",
    }, headers=h1)
    token = invite_resp.json()["token"]
    await sec_client.post(f"/api/v1/groups/invitations/{token}/accept", headers=h2)

    # Member tries to invite someone else
    resp = await sec_client.post(f"/api/v1/groups/{group_id}/invite", json={
        "email": "victim5@test.com",
        "role": "member",
    }, headers=h2)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_member_cannot_change_roles(sec_client):
    """Non-admin member cannot change roles."""
    h1 = await _register_and_login(sec_client, "admin6@test.com", display_name="Admin6")
    h2 = await _register_and_login(sec_client, "member6@test.com", display_name="Member6")

    create_resp = await sec_client.post("/api/v1/groups", json={
        "name": "Role Group", "type": "family",
    }, headers=h1)
    group_id = create_resp.json()["id"]

    # Get admin's user_id
    me_resp = await sec_client.get("/api/v1/auth/me", headers=h1)
    me_resp.json()["id"]

    # Admin invites member
    invite_resp = await sec_client.post(f"/api/v1/groups/{group_id}/invite", json={
        "email": "member6@test.com",
        "role": "member",
    }, headers=h1)
    token = invite_resp.json()["token"]
    await sec_client.post(f"/api/v1/groups/invitations/{token}/accept", headers=h2)

    # Member tries to promote themselves
    me2 = await sec_client.get("/api/v1/auth/me", headers=h2)
    member_user_id = me2.json()["id"]

    resp = await sec_client.patch(
        f"/api/v1/groups/{group_id}/members/{member_user_id}/role",
        json={"role": "parent"},
        headers=h2,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_deleted_user_token_rejected(sec_client):
    """After account deletion, old tokens are rejected."""
    headers = await _register_and_login(sec_client, "deleted@test.com", display_name="Delete Me")

    # Verify token works
    resp = await sec_client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200

    # Delete account
    await sec_client.delete("/api/v1/auth/account", headers=headers)

    # Old token should be rejected
    resp = await sec_client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code in (401, 404)


@pytest.mark.asyncio
async def test_unauthenticated_cannot_list_groups(sec_client):
    """Unauthenticated requests cannot access groups."""
    resp = await sec_client.get("/api/v1/groups")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_cannot_create_group(sec_client):
    """Unauthenticated requests cannot create groups."""
    resp = await sec_client.post("/api/v1/groups", json={
        "name": "Hacker Group", "type": "family",
    })
    assert resp.status_code == 401
