"""End-to-end tests for the FERPA compliance module."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group, GroupMember
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def e2e_engine():
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
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def e2e_session(e2e_engine):
    async_session_maker = sessionmaker(
        e2e_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def school_data(e2e_session):
    """Create a school admin user, group, and a student member."""
    user_id = uuid.uuid4()
    school_id = uuid.uuid4()
    member_id = uuid.uuid4()

    user = User(
        id=user_id,
        email=f"ferpa-school-{uuid.uuid4().hex[:8]}@example.com",
        display_name="School Admin",
        account_type="school",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()

    group = Group(
        id=school_id,
        name="FERPA Test School",
        type="school",
        owner_id=user_id,
        settings={},
    )
    e2e_session.add(group)
    await e2e_session.flush()

    member = GroupMember(
        id=member_id,
        group_id=school_id,
        user_id=None,
        role="member",
        display_name="Test Student",
    )
    e2e_session.add(member)
    await e2e_session.flush()

    return {
        "user_id": user_id,
        "school_id": school_id,
        "member_id": member_id,
    }


@pytest_asyncio.fixture
async def family_data(e2e_session):
    """Create a family user for 403 tests."""
    user_id = uuid.uuid4()

    user = User(
        id=user_id,
        email=f"ferpa-family-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Family Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()

    return {"user_id": user_id}


def _make_client(e2e_engine, e2e_session, user_id, group_id=None):
    app = create_app()

    async def get_db_override():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=user_id,
            group_id=group_id,
            role="admin",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest_asyncio.fixture
async def school_client(e2e_engine, e2e_session, school_data):
    async with _make_client(
        e2e_engine, e2e_session, school_data["user_id"], school_data["school_id"],
    ) as c:
        yield c


@pytest_asyncio.fixture
async def family_client(e2e_engine, e2e_session, family_data):
    async with _make_client(
        e2e_engine, e2e_session, family_data["user_id"], None,
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Educational Records
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_educational_record(school_client, school_data):
    resp = await school_client.post("/api/v1/ferpa/records", json={
        "member_id": str(school_data["member_id"]),
        "record_type": "ai_interaction",
        "title": "ChatGPT Usage Log",
        "description": "Student interaction with ChatGPT during class",
        "is_directory_info": False,
        "classification": "protected",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["record_type"] == "ai_interaction"
    assert data["title"] == "ChatGPT Usage Log"
    assert data["is_directory_info"] is False
    assert data["classification"] == "protected"
    assert data["group_id"] == str(school_data["school_id"])
    assert data["member_id"] == str(school_data["member_id"])
    assert data["created_by"] == str(school_data["user_id"])


@pytest.mark.asyncio
async def test_list_educational_records(school_client, school_data):
    # Create two records
    for title in ["Record A", "Record B"]:
        resp = await school_client.post("/api/v1/ferpa/records", json={
            "member_id": str(school_data["member_id"]),
            "record_type": "academic",
            "title": title,
        })
        assert resp.status_code == 201, resp.text

    resp = await school_client.get("/api/v1/ferpa/records")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 2
    # Most recent first
    titles = [r["title"] for r in data]
    assert "Record A" in titles
    assert "Record B" in titles


# ---------------------------------------------------------------------------
# Access Logs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_access_log(school_client, school_data):
    # First create a record to reference
    rec_resp = await school_client.post("/api/v1/ferpa/records", json={
        "member_id": str(school_data["member_id"]),
        "record_type": "safety_alert",
        "title": "Safety Alert Record",
    })
    assert rec_resp.status_code == 201
    record_id = rec_resp.json()["id"]

    resp = await school_client.post("/api/v1/ferpa/access-log", json={
        "record_id": record_id,
        "access_type": "view",
        "purpose": "Reviewing student safety alerts for quarterly report",
        "legitimate_interest": "school_official",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["access_type"] == "view"
    assert data["purpose"] == "Reviewing student safety alerts for quarterly report"
    assert data["legitimate_interest"] == "school_official"
    assert data["record_id"] == record_id
    assert data["accessor_user_id"] == str(school_data["user_id"])


@pytest.mark.asyncio
async def test_list_access_logs(school_client, school_data):
    # Create a record
    rec_resp = await school_client.post("/api/v1/ferpa/records", json={
        "member_id": str(school_data["member_id"]),
        "record_type": "behavioral",
        "title": "Behavioral Record",
    })
    record_id = rec_resp.json()["id"]

    # Log two accesses
    for purpose in ["View for counselor", "Export for parent"]:
        resp = await school_client.post("/api/v1/ferpa/access-log", json={
            "record_id": record_id,
            "access_type": "view",
            "purpose": purpose,
        })
        assert resp.status_code == 201

    resp = await school_client.get("/api/v1/ferpa/access-log")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_access_logs_filter_by_member(school_client, school_data):
    """Access logs can be filtered by member_id via query param."""
    # Create a record
    rec_resp = await school_client.post("/api/v1/ferpa/records", json={
        "member_id": str(school_data["member_id"]),
        "record_type": "academic",
        "title": "Grades",
    })
    record_id = rec_resp.json()["id"]

    # Log an access
    await school_client.post("/api/v1/ferpa/access-log", json={
        "record_id": record_id,
        "access_type": "view",
        "purpose": "Grade review",
    })

    # Filter by the member
    resp = await school_client.get(
        "/api/v1/ferpa/access-log",
        params={"member_id": str(school_data["member_id"])},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Filter by a non-existent member
    resp = await school_client.get(
        "/api/v1/ferpa/access-log",
        params={"member_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 0


# ---------------------------------------------------------------------------
# Data Sharing Agreements
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_data_sharing_agreement(school_client, school_data):
    resp = await school_client.post("/api/v1/ferpa/sharing-agreements", json={
        "third_party_name": "EdTech Corp",
        "purpose": "Learning analytics platform integration",
        "data_elements": {"fields": ["name", "grade", "ai_usage_summary"]},
        "legal_basis": "school_official",
        "effective_date": "2026-01-01T00:00:00Z",
        "expiration_date": "2027-01-01T00:00:00Z",
        "terms": {"data_deletion_on_expiry": True},
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["third_party_name"] == "EdTech Corp"
    assert data["legal_basis"] == "school_official"
    assert data["status"] == "active"
    assert data["created_by"] == str(school_data["user_id"])


@pytest.mark.asyncio
async def test_list_data_sharing_agreements(school_client, school_data):
    # Create two agreements
    for name in ["Vendor A", "Vendor B"]:
        resp = await school_client.post("/api/v1/ferpa/sharing-agreements", json={
            "third_party_name": name,
            "purpose": "Analytics",
            "data_elements": {"fields": ["name"]},
            "legal_basis": "consent",
            "effective_date": "2026-01-01T00:00:00Z",
        })
        assert resp.status_code == 201

    resp = await school_client.get("/api/v1/ferpa/sharing-agreements")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 2


# ---------------------------------------------------------------------------
# Annual Notification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_annual_notification(school_client, school_data):
    resp = await school_client.post("/api/v1/ferpa/annual-notification", json={
        "school_year": "2025-2026",
        "template_version": 2,
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["school_year"] == "2025-2026"
    assert data["template_version"] == 2
    assert data["notification_method"] == "email"
    assert data["recipient_count"] == 0


# ---------------------------------------------------------------------------
# Authorization: family users get 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_family_user_forbidden_records(family_client):
    resp = await family_client.get("/api/v1/ferpa/records")
    assert resp.status_code == 403
    assert "school account" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_family_user_forbidden_create_record(family_client):
    resp = await family_client.post("/api/v1/ferpa/records", json={
        "member_id": str(uuid.uuid4()),
        "record_type": "academic",
        "title": "Should fail",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_family_user_forbidden_access_log(family_client):
    resp = await family_client.get("/api/v1/ferpa/access-log")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_family_user_forbidden_sharing_agreements(family_client):
    resp = await family_client.get("/api/v1/ferpa/sharing-agreements")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_family_user_forbidden_annual_notification(family_client):
    resp = await family_client.post("/api/v1/ferpa/annual-notification", json={
        "school_year": "2025-2026",
    })
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_annual_notification_invalid_school_year(school_client):
    resp = await school_client.post("/api/v1/ferpa/annual-notification", json={
        "school_year": "2025",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_record_missing_title(school_client, school_data):
    resp = await school_client.post("/api/v1/ferpa/records", json={
        "member_id": str(school_data["member_id"]),
        "record_type": "academic",
        # title missing
    })
    assert resp.status_code == 422
