"""E2E tests for the school board compliance PDF report endpoint.

Tests cover: PDF response, content type, auth requirement,
valid PDF bytes, and Content-Disposition header.
"""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_login(client, email="schoolboard@test.com"):
    """Register a user and return the access token."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "School Admin",
        "account_type": "school",
        "privacy_notice_accepted": True,
    })
    return reg.json()["access_token"]


async def _create_group(client, headers):
    """Create a school group and return the group_id."""
    grp = await client.post("/api/v1/groups", json={
        "name": "Test School District",
        "type": "school",
    }, headers=headers)
    return grp.json()["id"]


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def sb_client():
    """Test client with committing DB session for school board report tests."""
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
        yield client

    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_school_board_report_returns_pdf(sb_client):
    """GET /reports/school-board/{id} returns PDF content type."""
    token = await _register_and_login(sb_client)
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(sb_client, headers)

    resp = await sb_client.get(
        f"/api/v1/reports/school-board/{gid}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_school_board_report_valid_pdf_bytes(sb_client):
    """Response body starts with PDF magic bytes (%PDF-)."""
    token = await _register_and_login(sb_client, "sbpdf@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(sb_client, headers)

    resp = await sb_client.get(
        f"/api/v1/reports/school-board/{gid}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.content[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_school_board_report_content_disposition(sb_client):
    """Response includes Content-Disposition attachment header."""
    token = await _register_and_login(sb_client, "sbdisp@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(sb_client, headers)

    resp = await sb_client.get(
        f"/api/v1/reports/school-board/{gid}", headers=headers
    )
    assert resp.status_code == 200
    disposition = resp.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert "school-board-report" in disposition


@pytest.mark.asyncio
async def test_school_board_report_requires_auth(sb_client):
    """Endpoint requires authentication (401 without token)."""
    fake_id = str(uuid4())
    resp = await sb_client.get(f"/api/v1/reports/school-board/{fake_id}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_school_board_report_has_substantial_content(sb_client):
    """Generated PDF has a reasonable size (not empty/trivial)."""
    token = await _register_and_login(sb_client, "sbsize@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(sb_client, headers)

    resp = await sb_client.get(
        f"/api/v1/reports/school-board/{gid}", headers=headers
    )
    assert resp.status_code == 200
    # A real PDF with multiple sections should be at least 2KB
    assert len(resp.content) > 2000


@pytest.mark.asyncio
async def test_school_board_report_invalid_uuid(sb_client):
    """Invalid UUID path parameter returns 422."""
    token = await _register_and_login(sb_client, "sbinvalid@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await sb_client.get(
        "/api/v1/reports/school-board/not-a-uuid", headers=headers
    )
    assert resp.status_code == 422
