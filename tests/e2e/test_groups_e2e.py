"""Groups module E2E tests — CRUD, member management, and edge cases."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


async def _register(client, email, account_type="family"):
    """Register and return auth token."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Test User",
        "account_type": account_type,
        "privacy_notice_accepted": True,
    })
    assert resp.status_code in (200, 201), f"Registration failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture
async def gc():
    """Groups E2E client with committing DB session."""
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


# ---------------------------------------------------------------------------
# Group CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_club_group(gc):
    """Create a club-type group."""
    token = await _register(gc, "club@example.com", "club")
    h = {"Authorization": f"Bearer {token}"}

    resp = await gc.post("/api/v1/groups", json={
        "name": "Chess Club",
        "type": "club",
    }, headers=h)
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "club"
    assert data["member_count"] == 1


@pytest.mark.asyncio
async def test_create_group_with_settings(gc):
    """Create a group with custom settings dict."""
    token = await _register(gc, "settings@example.com")
    h = {"Authorization": f"Bearer {token}"}

    resp = await gc.post("/api/v1/groups", json={
        "name": "Custom Family",
        "type": "family",
        "settings": {"notifications": True, "theme": "dark"},
    }, headers=h)
    assert resp.status_code == 201
    assert resp.json()["settings"]["theme"] == "dark"


@pytest.mark.asyncio
async def test_update_group_settings(gc):
    """Update group settings via PATCH."""
    token = await _register(gc, "updsettings@example.com")
    h = {"Authorization": f"Bearer {token}"}

    create = await gc.post("/api/v1/groups", json={
        "name": "Fam", "type": "family",
    }, headers=h)
    gid = create.json()["id"]

    resp = await gc.patch(f"/api/v1/groups/{gid}", json={
        "settings": {"bedtime": "21:00"},
    }, headers=h)
    assert resp.status_code == 200
    assert resp.json()["settings"]["bedtime"] == "21:00"


@pytest.mark.asyncio
async def test_delete_group_then_not_found(gc):
    """Deleted group is not accessible afterwards."""
    token = await _register(gc, "delnf@example.com")
    h = {"Authorization": f"Bearer {token}"}

    create = await gc.post("/api/v1/groups", json={
        "name": "Gone", "type": "family",
    }, headers=h)
    gid = create.json()["id"]

    del_resp = await gc.delete(f"/api/v1/groups/{gid}", headers=h)
    assert del_resp.status_code == 204

    get_resp = await gc.get(f"/api/v1/groups/{gid}", headers=h)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_groups_includes_auto_created(gc):
    """Family registration auto-creates a group; list returns it."""
    token = await _register(gc, "empty@example.com")
    h = {"Authorization": f"Bearer {token}"}

    resp = await gc.get("/api/v1/groups", headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["type"] == "family"


@pytest.mark.asyncio
async def test_invalid_group_type_returns_422(gc):
    """Invalid group type returns 422 validation error."""
    token = await _register(gc, "badtype@example.com")
    h = {"Authorization": f"Bearer {token}"}

    resp = await gc.post("/api/v1/groups", json={
        "name": "Bad", "type": "invalid_type",
    }, headers=h)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Member Management
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_family_member_cap_enforcement(gc):
    """Family groups enforce 5-member cap."""
    token = await _register(gc, "cap@example.com")
    h = {"Authorization": f"Bearer {token}"}

    create = await gc.post("/api/v1/groups", json={
        "name": "Full Family", "type": "family",
    }, headers=h)
    gid = create.json()["id"]

    # Owner is member #1, add 4 more to hit cap of 5
    for i in range(4):
        resp = await gc.post(f"/api/v1/groups/{gid}/members", json={
            "display_name": f"Child {i}",
            "role": "member",
        }, headers=h)
        assert resp.status_code == 201, f"Failed adding member {i}: {resp.text}"

    # 6th member should fail
    resp = await gc.post(f"/api/v1/groups/{gid}/members", json={
        "display_name": "Too Many",
        "role": "member",
    }, headers=h)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_remove_member_and_verify(gc):
    """Remove a member, then verify member list is shorter."""
    token = await _register(gc, "rmverify@example.com")
    h = {"Authorization": f"Bearer {token}"}

    create = await gc.post("/api/v1/groups", json={
        "name": "Family", "type": "family",
    }, headers=h)
    gid = create.json()["id"]

    add = await gc.post(f"/api/v1/groups/{gid}/members", json={
        "display_name": "Temp", "role": "member",
    }, headers=h)
    mid = add.json()["id"]

    await gc.delete(f"/api/v1/groups/{gid}/members/{mid}", headers=h)

    members = await gc.get(f"/api/v1/groups/{gid}/members", headers=h)
    assert len(members.json()) == 1  # Only owner remains


@pytest.mark.asyncio
async def test_add_member_with_date_of_birth(gc):
    """Add a minor member with date_of_birth field."""
    token = await _register(gc, "dob@example.com")
    h = {"Authorization": f"Bearer {token}"}

    create = await gc.post("/api/v1/groups", json={
        "name": "Family", "type": "family",
    }, headers=h)
    gid = create.json()["id"]

    resp = await gc.post(f"/api/v1/groups/{gid}/members", json={
        "display_name": "Young Child",
        "role": "member",
        "date_of_birth": "2018-06-15T00:00:00",
    }, headers=h)
    assert resp.status_code == 201
    assert resp.json()["date_of_birth"] is not None


@pytest.mark.asyncio
async def test_unauthenticated_access_returns_401(gc):
    """Requests without auth token return 401."""
    resp = await gc.get("/api/v1/groups")
    assert resp.status_code == 401

    resp = await gc.post("/api/v1/groups", json={
        "name": "Nope", "type": "family",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cross_group_access_blocked(gc):
    """User A cannot access User B's group."""
    token_a = await _register(gc, "usera@example.com")
    token_b = await _register(gc, "userb@example.com")
    ha = {"Authorization": f"Bearer {token_a}"}
    hb = {"Authorization": f"Bearer {token_b}"}

    create = await gc.post("/api/v1/groups", json={
        "name": "A Family", "type": "family",
    }, headers=ha)
    gid = create.json()["id"]

    # User B tries to access User A's group
    resp = await gc.get(f"/api/v1/groups/{gid}", headers=hb)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_invitation_and_verify(gc):
    """Create an invitation and verify its fields."""
    token = await _register(gc, "invitenew@example.com")
    h = {"Authorization": f"Bearer {token}"}

    create = await gc.post("/api/v1/groups", json={
        "name": "Invite Family", "type": "family",
    }, headers=h)
    gid = create.json()["id"]

    resp = await gc.post(f"/api/v1/groups/{gid}/invite", json={
        "email": "newmember@example.com",
        "role": "parent",
    }, headers=h)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newmember@example.com"
    assert data["role"] == "parent"
    assert data["status"] == "pending"
    assert data["token"]  # token is present


@pytest.mark.asyncio
async def test_change_role_to_parent(gc):
    """Promote a member to parent role."""
    token = await _register(gc, "promote@example.com")
    h = {"Authorization": f"Bearer {token}"}

    create = await gc.post("/api/v1/groups", json={
        "name": "Family", "type": "family",
    }, headers=h)
    gid = create.json()["id"]

    add = await gc.post(f"/api/v1/groups/{gid}/members", json={
        "display_name": "Co-parent", "role": "member",
    }, headers=h)
    mid = add.json()["id"]

    resp = await gc.patch(f"/api/v1/groups/{gid}/members/{mid}/role", json={
        "role": "parent",
    }, headers=h)
    assert resp.status_code == 200
    assert resp.json()["role"] == "parent"
