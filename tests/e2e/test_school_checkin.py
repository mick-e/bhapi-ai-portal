"""End-to-end tests for school check-in: parent consent, check-in/out, attendance."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group, GroupMember
from src.location.models import Geofence
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def ci_engine():
    """In-memory SQLite engine for school check-in E2E tests."""
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
async def ci_session(ci_engine):
    """Session for school check-in E2E tests."""
    session = AsyncSession(ci_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def ci_data(ci_session):
    """Seed parent user, family group, school group, child member, and school geofence."""
    parent = User(
        id=uuid.uuid4(),
        email=f"parent-ci-{uuid.uuid4().hex[:8]}@school.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="CI Parent",
        account_type="family",
        email_verified=True,
        mfa_enabled=False,
    )
    ci_session.add(parent)

    school_owner = User(
        id=uuid.uuid4(),
        email=f"school-ci-{uuid.uuid4().hex[:8]}@school.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="CI School Admin",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    ci_session.add(school_owner)
    await ci_session.flush()

    family_group = Group(
        id=uuid.uuid4(),
        name="CI Family",
        type="family",
        owner_id=parent.id,
    )
    ci_session.add(family_group)

    school_group = Group(
        id=uuid.uuid4(),
        name="CI School",
        type="school",
        owner_id=school_owner.id,
    )
    ci_session.add(school_group)
    await ci_session.flush()

    child = GroupMember(
        id=uuid.uuid4(),
        group_id=family_group.id,
        user_id=None,
        role="child",
        display_name="CI Child",
    )
    ci_session.add(child)
    await ci_session.flush()

    # Geofence belongs to the school_group so school gets check-in events
    school_geofence = Geofence(
        id=uuid.uuid4(),
        group_id=school_group.id,
        member_id=child.id,
        name="CI School Gate",
        latitude=51.5,
        longitude=-0.1,
        radius_meters=50.0,
        notify_on_enter=True,
        notify_on_exit=True,
    )
    ci_session.add(school_geofence)
    await ci_session.flush()

    return {
        "parent": parent,
        "school_owner": school_owner,
        "family_group": family_group,
        "school_group": school_group,
        "child": child,
        "geofence": school_geofence,
    }


def _make_client(ci_engine, ci_session, user_id, group_id, role="owner"):
    """Return an AsyncClient context manager with auth + DB overrides."""
    app = create_app()

    async def get_db_override():
        try:
            yield ci_session
            await ci_session.commit()
        except Exception:
            await ci_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(user_id=user_id, group_id=group_id, role=role)

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


# ---------------------------------------------------------------------------
# Test 1: Grant consent → check-in succeeds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consent_then_checkin_succeeds(ci_engine, ci_session, ci_data):
    """Create consent then check-in succeeds (201)."""
    d = ci_data

    async with _make_client(ci_engine, ci_session, d["parent"].id, d["family_group"].id) as client:
        # Grant consent
        resp = await client.post("/api/v1/location/school-consent", json={
            "member_id": str(d["child"].id),
            "school_group_id": str(d["school_group"].id),
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["member_id"] == str(d["child"].id)
        assert body["revoked_at"] is None

        # Check-in succeeds now that consent exists
        resp2 = await client.post("/api/v1/location/check-in", json={
            "member_id": str(d["child"].id),
            "geofence_id": str(d["geofence"].id),
        })
        assert resp2.status_code == 201
        ci_body = resp2.json()
        assert ci_body["member_id"] == str(d["child"].id)
        assert ci_body["check_out_at"] is None


# ---------------------------------------------------------------------------
# Test 2: Check-in without consent returns 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkin_without_consent_returns_403(ci_engine, ci_session, ci_data):
    """Check-in without parental consent must return 403."""
    d = ci_data

    async with _make_client(ci_engine, ci_session, d["parent"].id, d["family_group"].id) as client:
        resp = await client.post("/api/v1/location/check-in", json={
            "member_id": str(d["child"].id),
            "geofence_id": str(d["geofence"].id),
        })
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test 3: Check-out matches the latest open check-in
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkout_matches_latest_checkin(ci_engine, ci_session, ci_data):
    """Check-out sets check_out_at on the open check-in record."""
    d = ci_data

    async with _make_client(ci_engine, ci_session, d["parent"].id, d["family_group"].id) as client:
        # Grant consent
        await client.post("/api/v1/location/school-consent", json={
            "member_id": str(d["child"].id),
            "school_group_id": str(d["school_group"].id),
        })

        # Check-in
        ci_resp = await client.post("/api/v1/location/check-in", json={
            "member_id": str(d["child"].id),
            "geofence_id": str(d["geofence"].id),
        })
        assert ci_resp.status_code == 201
        checkin_id = ci_resp.json()["id"]

        # Check-out
        co_resp = await client.post("/api/v1/location/check-out", json={
            "member_id": str(d["child"].id),
            "geofence_id": str(d["geofence"].id),
        })
        assert co_resp.status_code == 200
        co_body = co_resp.json()
        assert co_body["id"] == checkin_id
        assert co_body["check_out_at"] is not None


# ---------------------------------------------------------------------------
# Test 4: School attendance returns timestamps only (no coordinates)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attendance_returns_timestamps_only(ci_engine, ci_session, ci_data):
    """School attendance endpoint returns timestamps — no lat/lng fields."""
    d = ci_data

    async with _make_client(ci_engine, ci_session, d["school_owner"].id, d["school_group"].id, role="school_admin") as client:
        # Grant consent and record a check-in as parent first
        async with _make_client(ci_engine, ci_session, d["parent"].id, d["family_group"].id) as parent_client:
            await parent_client.post("/api/v1/location/school-consent", json={
                "member_id": str(d["child"].id),
                "school_group_id": str(d["school_group"].id),
            })
            await parent_client.post("/api/v1/location/check-in", json={
                "member_id": str(d["child"].id),
                "geofence_id": str(d["geofence"].id),
            })

        today = datetime.now(timezone.utc).date().isoformat() + "T00:00:00Z"
        resp = await client.get(
            f"/api/v1/location/school/{d['school_group'].id}/attendance",
            params={"date": today},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

        record = body["items"][0]
        # Must have check-in time
        assert "check_in_at" in record
        # Must NOT have coordinates
        assert "latitude" not in record
        assert "longitude" not in record
        assert "accuracy" not in record


# ---------------------------------------------------------------------------
# Test 5: Revoke consent → subsequent check-in fails
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revoke_consent_blocks_future_checkins(ci_engine, ci_session, ci_data):
    """Revoking consent makes future check-ins return 403."""
    d = ci_data

    async with _make_client(ci_engine, ci_session, d["parent"].id, d["family_group"].id) as client:
        # Grant consent
        grant_resp = await client.post("/api/v1/location/school-consent", json={
            "member_id": str(d["child"].id),
            "school_group_id": str(d["school_group"].id),
        })
        assert grant_resp.status_code == 201
        consent_id = grant_resp.json()["id"]

        # Check-in succeeds
        ci_resp = await client.post("/api/v1/location/check-in", json={
            "member_id": str(d["child"].id),
            "geofence_id": str(d["geofence"].id),
        })
        assert ci_resp.status_code == 201

        # Check-out to close the open record
        await client.post("/api/v1/location/check-out", json={
            "member_id": str(d["child"].id),
            "geofence_id": str(d["geofence"].id),
        })

        # Revoke consent
        revoke_resp = await client.delete(f"/api/v1/location/school-consent/{consent_id}")
        assert revoke_resp.status_code == 200
        assert revoke_resp.json()["revoked_at"] is not None

        # Check-in now fails
        ci_resp2 = await client.post("/api/v1/location/check-in", json={
            "member_id": str(d["child"].id),
            "geofence_id": str(d["geofence"].id),
        })
        assert ci_resp2.status_code == 403


# ---------------------------------------------------------------------------
# Test 6: Full flow — consent → check-in → check-out → verify attendance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_attendance_flow(ci_engine, ci_session, ci_data):
    """Full flow: consent → check-in → check-out → attendance shows complete record."""
    d = ci_data

    async with _make_client(ci_engine, ci_session, d["parent"].id, d["family_group"].id) as client:
        # Grant consent
        await client.post("/api/v1/location/school-consent", json={
            "member_id": str(d["child"].id),
            "school_group_id": str(d["school_group"].id),
        })

        # Check-in
        ci_resp = await client.post("/api/v1/location/check-in", json={
            "member_id": str(d["child"].id),
            "geofence_id": str(d["geofence"].id),
        })
        assert ci_resp.status_code == 201

        # Check-out
        co_resp = await client.post("/api/v1/location/check-out", json={
            "member_id": str(d["child"].id),
            "geofence_id": str(d["geofence"].id),
        })
        assert co_resp.status_code == 200

    # School admin sees attendance with both check-in and check-out timestamps
    async with _make_client(ci_engine, ci_session, d["school_owner"].id, d["school_group"].id, role="school_admin") as school_client:
        today = datetime.now(timezone.utc).date().isoformat() + "T00:00:00Z"
        att_resp = await school_client.get(
            f"/api/v1/location/school/{d['school_group'].id}/attendance",
            params={"date": today},
        )
        assert att_resp.status_code == 200
        body = att_resp.json()
        assert body["total"] >= 1
        record = body["items"][0]
        assert record["check_in_at"] is not None
        assert record["check_out_at"] is not None


# ---------------------------------------------------------------------------
# Test 7: Grant consent is idempotent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_grant_consent_idempotent(ci_engine, ci_session, ci_data):
    """Granting consent twice returns same active consent."""
    d = ci_data

    async with _make_client(ci_engine, ci_session, d["parent"].id, d["family_group"].id) as client:
        resp1 = await client.post("/api/v1/location/school-consent", json={
            "member_id": str(d["child"].id),
            "school_group_id": str(d["school_group"].id),
        })
        assert resp1.status_code == 201
        id1 = resp1.json()["id"]

        resp2 = await client.post("/api/v1/location/school-consent", json={
            "member_id": str(d["child"].id),
            "school_group_id": str(d["school_group"].id),
        })
        assert resp2.status_code == 201
        # Same consent ID returned (idempotent)
        assert resp2.json()["id"] == id1


# ---------------------------------------------------------------------------
# Test 8: Revoke unknown consent returns 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revoke_unknown_consent_404(ci_engine, ci_session, ci_data):
    """Revoking a non-existent consent returns 404."""
    d = ci_data

    async with _make_client(ci_engine, ci_session, d["parent"].id, d["family_group"].id) as client:
        resp = await client.delete(f"/api/v1/location/school-consent/{uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 9: Check-out without open check-in returns 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkout_without_checkin_404(ci_engine, ci_session, ci_data):
    """Check-out when no open check-in exists returns 404."""
    d = ci_data

    async with _make_client(ci_engine, ci_session, d["parent"].id, d["family_group"].id) as client:
        # Grant consent so we can attempt check-out
        await client.post("/api/v1/location/school-consent", json={
            "member_id": str(d["child"].id),
            "school_group_id": str(d["school_group"].id),
        })

        # No check-in exists — check-out should fail
        resp = await client.post("/api/v1/location/check-out", json={
            "member_id": str(d["child"].id),
            "geofence_id": str(d["geofence"].id),
        })
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 10: Attendance for empty day returns empty list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attendance_empty_day(ci_engine, ci_session, ci_data):
    """Attendance for a day with no check-ins returns empty items list."""
    d = ci_data

    async with _make_client(ci_engine, ci_session, d["school_owner"].id, d["school_group"].id, role="school_admin") as client:
        past_date = "2020-01-01T00:00:00Z"
        resp = await client.get(
            f"/api/v1/location/school/{d['school_group'].id}/attendance",
            params={"date": past_date},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []


# ---------------------------------------------------------------------------
# Test 11: Check-in for unknown geofence returns 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkin_unknown_geofence_404(ci_engine, ci_session, ci_data):
    """Check-in with an unknown geofence_id returns 404."""
    d = ci_data

    async with _make_client(ci_engine, ci_session, d["parent"].id, d["family_group"].id) as client:
        resp = await client.post("/api/v1/location/check-in", json={
            "member_id": str(d["child"].id),
            "geofence_id": str(uuid.uuid4()),
        })
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 12: Re-grant consent after revocation reactivates it
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regrant_after_revoke(ci_engine, ci_session, ci_data):
    """Parent can re-grant consent after revoking it."""
    d = ci_data

    async with _make_client(ci_engine, ci_session, d["parent"].id, d["family_group"].id) as client:
        # Grant
        grant_resp = await client.post("/api/v1/location/school-consent", json={
            "member_id": str(d["child"].id),
            "school_group_id": str(d["school_group"].id),
        })
        consent_id = grant_resp.json()["id"]

        # Revoke
        await client.delete(f"/api/v1/location/school-consent/{consent_id}")

        # Re-grant
        regrant_resp = await client.post("/api/v1/location/school-consent", json={
            "member_id": str(d["child"].id),
            "school_group_id": str(d["school_group"].id),
        })
        assert regrant_resp.status_code == 201
        assert regrant_resp.json()["revoked_at"] is None

        # Check-in should succeed again
        ci_resp = await client.post("/api/v1/location/check-in", json={
            "member_id": str(d["child"].id),
            "geofence_id": str(d["geofence"].id),
        })
        assert ci_resp.status_code == 201
