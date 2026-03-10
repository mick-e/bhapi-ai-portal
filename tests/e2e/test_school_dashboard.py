"""School admin dashboard E2E tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


async def _register_and_login(client, email="test@example.com", account_type="school"):
    """Helper: register and return token + user data."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Test User",
        "account_type": account_type,
    })
    data = reg.json()
    return data["access_token"], data["user"]["group_id"]


async def _setup_school(client, token, group_id):
    """Helper: return group_id and headers for school tests."""
    headers = {"Authorization": f"Bearer {token}"}
    return group_id, headers


@pytest.fixture
async def school_client():
    """School test client with committing DB session."""
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


# --- Class CRUD ---

@pytest.mark.asyncio
async def test_create_class(school_client):
    """Create a class in a school group."""
    token, gid = await _register_and_login(school_client, "admin@example.com")
    group_id, headers = await _setup_school(school_client, token, gid)

    response = await school_client.post("/api/v1/school/classes", json={
        "name": "Year 8 Science",
        "grade_level": "Year 8",
        "academic_year": "2025-2026",
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Year 8 Science"
    assert data["grade_level"] == "Year 8"
    assert data["academic_year"] == "2025-2026"
    assert data["member_count"] == 0


@pytest.mark.asyncio
async def test_list_classes(school_client):
    """List classes in a school group."""
    token, gid = await _register_and_login(school_client, "list@example.com")
    group_id, headers = await _setup_school(school_client, token, gid)

    # Create two classes
    await school_client.post("/api/v1/school/classes", json={
        "name": "Year 7 Maths",
    }, headers=headers)
    await school_client.post("/api/v1/school/classes", json={
        "name": "Year 8 English",
    }, headers=headers)

    response = await school_client.get("/api/v1/school/classes", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = [c["name"] for c in data]
    assert "Year 7 Maths" in names
    assert "Year 8 English" in names


@pytest.mark.asyncio
async def test_create_class_without_optional_fields(school_client):
    """Create a class with only required fields."""
    token, gid = await _register_and_login(school_client, "minimal@example.com")
    group_id, headers = await _setup_school(school_client, token, gid)

    response = await school_client.post("/api/v1/school/classes", json={
        "name": "Assembly Group",
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Assembly Group"
    assert data["grade_level"] is None
    assert data["academic_year"] is None


# --- Member Management ---

@pytest.mark.asyncio
async def test_add_member_to_class(school_client):
    """Add a group member to a class."""
    token, gid = await _register_and_login(school_client, "addmem@example.com")
    group_id, headers = await _setup_school(school_client, token, gid)

    # Create a class
    cls_resp = await school_client.post("/api/v1/school/classes", json={
        "name": "Year 9 History",
    }, headers=headers)
    class_id = cls_resp.json()["id"]

    # Add a member to the group first
    mem_resp = await school_client.post(f"/api/v1/groups/{group_id}/members", json={
        "display_name": "Alice Student",
        "role": "member",
    }, headers=headers)
    member_id = mem_resp.json()["id"]

    # Add member to class
    response = await school_client.post(
        f"/api/v1/school/classes/{class_id}/members",
        json={"member_id": member_id},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["member_id"] == member_id
    assert data["display_name"] == "Alice Student"


@pytest.mark.asyncio
async def test_add_duplicate_member_to_class(school_client):
    """Adding same member twice returns 422."""
    token, gid = await _register_and_login(school_client, "dup@example.com")
    group_id, headers = await _setup_school(school_client, token, gid)

    cls_resp = await school_client.post("/api/v1/school/classes", json={
        "name": "Art Class",
    }, headers=headers)
    class_id = cls_resp.json()["id"]

    mem_resp = await school_client.post(f"/api/v1/groups/{group_id}/members", json={
        "display_name": "Bob Student",
        "role": "member",
    }, headers=headers)
    member_id = mem_resp.json()["id"]

    # First add succeeds
    resp1 = await school_client.post(
        f"/api/v1/school/classes/{class_id}/members",
        json={"member_id": member_id},
        headers=headers,
    )
    assert resp1.status_code == 201

    # Second add fails
    resp2 = await school_client.post(
        f"/api/v1/school/classes/{class_id}/members",
        json={"member_id": member_id},
        headers=headers,
    )
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_remove_member_from_class(school_client):
    """Remove a member from a class."""
    token, gid = await _register_and_login(school_client, "remove@example.com")
    group_id, headers = await _setup_school(school_client, token, gid)

    cls_resp = await school_client.post("/api/v1/school/classes", json={
        "name": "Music Class",
    }, headers=headers)
    class_id = cls_resp.json()["id"]

    mem_resp = await school_client.post(f"/api/v1/groups/{group_id}/members", json={
        "display_name": "Charlie Student",
        "role": "member",
    }, headers=headers)
    member_id = mem_resp.json()["id"]

    # Add then remove
    await school_client.post(
        f"/api/v1/school/classes/{class_id}/members",
        json={"member_id": member_id},
        headers=headers,
    )

    response = await school_client.delete(
        f"/api/v1/school/classes/{class_id}/members/{member_id}",
        headers=headers,
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_remove_nonexistent_member_from_class(school_client):
    """Removing a member not in the class returns 404."""
    token, gid = await _register_and_login(school_client, "noremove@example.com")
    group_id, headers = await _setup_school(school_client, token, gid)

    cls_resp = await school_client.post("/api/v1/school/classes", json={
        "name": "Drama",
    }, headers=headers)
    class_id = cls_resp.json()["id"]

    mem_resp = await school_client.post(f"/api/v1/groups/{group_id}/members", json={
        "display_name": "Dave Student",
        "role": "member",
    }, headers=headers)
    member_id = mem_resp.json()["id"]

    response = await school_client.delete(
        f"/api/v1/school/classes/{class_id}/members/{member_id}",
        headers=headers,
    )
    assert response.status_code == 404


# --- Risks ---

@pytest.mark.asyncio
async def test_get_class_risks_empty(school_client):
    """Get risks for a class with no risk events."""
    token, gid = await _register_and_login(school_client, "risks@example.com")
    group_id, headers = await _setup_school(school_client, token, gid)

    cls_resp = await school_client.post("/api/v1/school/classes", json={
        "name": "Year 10 PE",
    }, headers=headers)
    class_id = cls_resp.json()["id"]

    response = await school_client.get(
        f"/api/v1/school/classes/{class_id}/risks",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_class_risks_with_members(school_client):
    """Get risks for a class — returns empty when no risk events exist."""
    token, gid = await _register_and_login(school_client, "riskm@example.com")
    group_id, headers = await _setup_school(school_client, token, gid)

    cls_resp = await school_client.post("/api/v1/school/classes", json={
        "name": "Year 11 ICT",
    }, headers=headers)
    class_id = cls_resp.json()["id"]

    # Add member to group and class
    mem_resp = await school_client.post(f"/api/v1/groups/{group_id}/members", json={
        "display_name": "Eve Student",
        "role": "member",
    }, headers=headers)
    member_id = mem_resp.json()["id"]

    await school_client.post(
        f"/api/v1/school/classes/{class_id}/members",
        json={"member_id": member_id},
        headers=headers,
    )

    response = await school_client.get(
        f"/api/v1/school/classes/{class_id}/risks",
        headers=headers,
    )
    assert response.status_code == 200
    # No risk events created so empty list
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_class_risks_nonexistent_class(school_client):
    """Get risks for non-existent class returns 404."""
    token, gid = await _register_and_login(school_client, "noclass@example.com")
    group_id, headers = await _setup_school(school_client, token, gid)

    response = await school_client.get(
        "/api/v1/school/classes/00000000-0000-0000-0000-000000000000/risks",
        headers=headers,
    )
    assert response.status_code == 404


# --- Safeguarding Report ---

@pytest.mark.asyncio
async def test_safeguarding_report_empty(school_client):
    """Safeguarding report with no risk events."""
    token, gid = await _register_and_login(school_client, "report@example.com")
    group_id, headers = await _setup_school(school_client, token, gid)

    response = await school_client.get(
        "/api/v1/school/safeguarding-report",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_risks"] == 0
    assert data["by_severity"] == {}
    assert data["by_category"] == {}
    assert data["flagged_students"] == []
    assert "period_start" in data
    assert "period_end" in data


# --- Access Control ---

@pytest.mark.asyncio
async def test_family_user_cannot_access_school_endpoints(school_client):
    """Family user cannot access school admin endpoints."""
    token, gid = await _register_and_login(school_client, "family@example.com", "family")
    headers = {"Authorization": f"Bearer {token}"}

    # Create a family group
    await school_client.post("/api/v1/groups", json={
        "name": "Smith Family",
        "type": "family",
    }, headers=headers)

    response = await school_client.get("/api/v1/school/classes", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_access_denied(school_client):
    """Unauthenticated requests are denied."""
    response = await school_client.get("/api/v1/school/classes")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_class_member_count_updates(school_client):
    """Member count updates when members are added to class."""
    token, gid = await _register_and_login(school_client, "count@example.com")
    group_id, headers = await _setup_school(school_client, token, gid)

    cls_resp = await school_client.post("/api/v1/school/classes", json={
        "name": "Year 7 Geography",
    }, headers=headers)
    class_id = cls_resp.json()["id"]

    # Add two members
    for name in ["Student A", "Student B"]:
        mem_resp = await school_client.post(f"/api/v1/groups/{group_id}/members", json={
            "display_name": name,
            "role": "member",
        }, headers=headers)
        member_id = mem_resp.json()["id"]
        await school_client.post(
            f"/api/v1/school/classes/{class_id}/members",
            json={"member_id": member_id},
            headers=headers,
        )

    # Verify count
    response = await school_client.get("/api/v1/school/classes", headers=headers)
    assert response.status_code == 200
    classes = response.json()
    geo_class = next(c for c in classes if c["name"] == "Year 7 Geography")
    assert geo_class["member_count"] == 2


@pytest.mark.asyncio
async def test_create_class_validation_empty_name(school_client):
    """Cannot create class with empty name."""
    token, gid = await _register_and_login(school_client, "valid@example.com")
    group_id, headers = await _setup_school(school_client, token, gid)

    response = await school_client.post("/api/v1/school/classes", json={
        "name": "",
    }, headers=headers)
    assert response.status_code == 422
