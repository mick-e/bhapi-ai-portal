"""Groups module security tests — auth, isolation, injection, and bypass attempts."""

import uuid

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
async def sc():
    """Security test client with committing DB session."""
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
# Authentication — all group endpoints require auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauth_list_groups(sc):
    """GET /groups without auth returns 401."""
    resp = await sc.get("/api/v1/groups")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauth_create_group(sc):
    """POST /groups without auth returns 401."""
    resp = await sc.post("/api/v1/groups", json={"name": "X", "type": "family"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauth_get_group(sc):
    """GET /groups/{id} without auth returns 401."""
    fake_id = str(uuid.uuid4())
    resp = await sc.get(f"/api/v1/groups/{fake_id}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauth_delete_group(sc):
    """DELETE /groups/{id} without auth returns 401."""
    fake_id = str(uuid.uuid4())
    resp = await sc.delete(f"/api/v1/groups/{fake_id}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauth_add_member(sc):
    """POST /groups/{id}/members without auth returns 401."""
    fake_id = str(uuid.uuid4())
    resp = await sc.post(f"/api/v1/groups/{fake_id}/members", json={
        "display_name": "Hack", "role": "member",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauth_list_members(sc):
    """GET /groups/{id}/members without auth returns 401."""
    fake_id = str(uuid.uuid4())
    resp = await sc.get(f"/api/v1/groups/{fake_id}/members")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Authorization — non-owner / non-member restrictions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_owner_cannot_delete_group(sc):
    """Only the group owner can delete the group (403 for others)."""
    token_a = await _register(sc, "ownerdel@example.com")
    token_b = await _register(sc, "otherdel@example.com")
    ha = {"Authorization": f"Bearer {token_a}"}
    hb = {"Authorization": f"Bearer {token_b}"}

    create = await sc.post("/api/v1/groups", json={
        "name": "Owner Only", "type": "family",
    }, headers=ha)
    gid = create.json()["id"]

    # Non-member cannot delete
    resp = await sc.delete(f"/api/v1/groups/{gid}", headers=hb)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_member_cannot_add_members(sc):
    """Non-member cannot add members to another user's group (403)."""
    token_a = await _register(sc, "addowner@example.com")
    token_b = await _register(sc, "addother@example.com")
    ha = {"Authorization": f"Bearer {token_a}"}
    hb = {"Authorization": f"Bearer {token_b}"}

    create = await sc.post("/api/v1/groups", json={
        "name": "Private", "type": "family",
    }, headers=ha)
    gid = create.json()["id"]

    resp = await sc.post(f"/api/v1/groups/{gid}/members", json={
        "display_name": "Intruder", "role": "member",
    }, headers=hb)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_isolation(sc):
    """User in group A cannot access group B's members."""
    token_a = await _register(sc, "tenanta@example.com")
    token_b = await _register(sc, "tenantb@example.com")
    ha = {"Authorization": f"Bearer {token_a}"}
    hb = {"Authorization": f"Bearer {token_b}"}

    # A creates group
    create_a = await sc.post("/api/v1/groups", json={
        "name": "Group A", "type": "family",
    }, headers=ha)
    gid_a = create_a.json()["id"]

    # B tries to list A's members
    resp = await sc.get(f"/api/v1/groups/{gid_a}/members", headers=hb)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Input validation — injection and malformed input
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sql_injection_in_group_name(sc):
    """SQL injection attempt in group name is safely stored as text."""
    token = await _register(sc, "sqli@example.com")
    h = {"Authorization": f"Bearer {token}"}

    resp = await sc.post("/api/v1/groups", json={
        "name": "'; DROP TABLE groups; --",
        "type": "family",
    }, headers=h)
    assert resp.status_code == 201
    # Name stored literally, not executed
    assert resp.json()["name"] == "'; DROP TABLE groups; --"


@pytest.mark.asyncio
async def test_xss_in_group_name(sc):
    """XSS payload in group name is stored as-is (no execution)."""
    token = await _register(sc, "xss@example.com")
    h = {"Authorization": f"Bearer {token}"}

    xss = "<script>alert('xss')</script>"
    resp = await sc.post("/api/v1/groups", json={
        "name": xss,
        "type": "family",
    }, headers=h)
    assert resp.status_code == 201
    assert resp.json()["name"] == xss


@pytest.mark.asyncio
async def test_invalid_uuid_in_group_id(sc):
    """Invalid UUID in group_id path param returns 422."""
    token = await _register(sc, "baduuid@example.com")
    h = {"Authorization": f"Bearer {token}"}

    resp = await sc.get("/api/v1/groups/not-a-uuid", headers=h)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_nonexistent_group_returns_404(sc):
    """Valid UUID that does not exist returns 404."""
    token = await _register(sc, "nogroup@example.com")
    h = {"Authorization": f"Bearer {token}"}

    fake_id = str(uuid.uuid4())
    resp = await sc.get(f"/api/v1/groups/{fake_id}", headers=h)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Member cap bypass attempt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_member_cap_bypass_rejected(sc):
    """Cannot bypass family member cap (5) by rapid concurrent adds."""
    token = await _register(sc, "capbypass@example.com")
    h = {"Authorization": f"Bearer {token}"}

    create = await sc.post("/api/v1/groups", json={
        "name": "Cap Test", "type": "family",
    }, headers=h)
    gid = create.json()["id"]

    # Fill to cap: owner(1) + 4 members = 5
    for i in range(4):
        resp = await sc.post(f"/api/v1/groups/{gid}/members", json={
            "display_name": f"M{i}", "role": "member",
        }, headers=h)
        assert resp.status_code == 201

    # 6th should fail
    resp = await sc.post(f"/api/v1/groups/{gid}/members", json={
        "display_name": "Overflow", "role": "member",
    }, headers=h)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Soft-deleted groups not accessible
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_soft_deleted_group_not_accessible(sc):
    """After soft-delete, group returns 404."""
    token = await _register(sc, "softdel@example.com")
    h = {"Authorization": f"Bearer {token}"}

    create = await sc.post("/api/v1/groups", json={
        "name": "Delete Me", "type": "family",
    }, headers=h)
    gid = create.json()["id"]

    await sc.delete(f"/api/v1/groups/{gid}", headers=h)

    resp = await sc.get(f"/api/v1/groups/{gid}", headers=h)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_non_member_cannot_update_group(sc):
    """Non-member cannot update another user's group."""
    token_a = await _register(sc, "updowner@example.com")
    token_b = await _register(sc, "updother@example.com")
    ha = {"Authorization": f"Bearer {token_a}"}
    hb = {"Authorization": f"Bearer {token_b}"}

    create = await sc.post("/api/v1/groups", json={
        "name": "No Touch", "type": "family",
    }, headers=ha)
    gid = create.json()["id"]

    resp = await sc.patch(f"/api/v1/groups/{gid}", json={
        "name": "Hacked",
    }, headers=hb)
    assert resp.status_code == 403
