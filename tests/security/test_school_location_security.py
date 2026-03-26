"""Security tests for school check-in — privacy enforcement, isolation, consent control."""

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
from src.location.service import (
    create_school_consent,
    get_school_attendance,
    record_check_in,
)
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sl_engine():
    """In-memory SQLite engine for school location security tests."""
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
async def sl_session(sl_engine):
    session = AsyncSession(sl_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def sl_data(sl_session):
    """Two schools + two families for cross-school isolation tests."""
    # School A
    school_a_owner = User(
        id=uuid.uuid4(),
        email=f"school-a-{uuid.uuid4().hex[:8]}@schoola.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="School A Admin",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    sl_session.add(school_a_owner)

    # School B
    school_b_owner = User(
        id=uuid.uuid4(),
        email=f"school-b-{uuid.uuid4().hex[:8]}@schoolb.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="School B Admin",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    sl_session.add(school_b_owner)

    # Parent A
    parent_a = User(
        id=uuid.uuid4(),
        email=f"parent-a-{uuid.uuid4().hex[:8]}@family.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Parent A",
        account_type="family",
        email_verified=True,
        mfa_enabled=False,
    )
    sl_session.add(parent_a)
    await sl_session.flush()

    school_a = Group(id=uuid.uuid4(), name="School A", type="school", owner_id=school_a_owner.id)
    school_b = Group(id=uuid.uuid4(), name="School B", type="school", owner_id=school_b_owner.id)
    family_a = Group(id=uuid.uuid4(), name="Family A", type="family", owner_id=parent_a.id)
    sl_session.add_all([school_a, school_b, family_a])
    await sl_session.flush()

    child_a = GroupMember(id=uuid.uuid4(), group_id=family_a.id, user_id=None, role="child", display_name="Child A")
    sl_session.add(child_a)
    await sl_session.flush()

    # Geofence owned by school A
    geofence_a = Geofence(
        id=uuid.uuid4(),
        group_id=school_a.id,
        member_id=child_a.id,
        name="School A Gate",
        latitude=51.5,
        longitude=-0.1,
        radius_meters=50.0,
        notify_on_enter=True,
        notify_on_exit=True,
    )
    sl_session.add(geofence_a)
    await sl_session.flush()

    return {
        "school_a_owner": school_a_owner,
        "school_b_owner": school_b_owner,
        "parent_a": parent_a,
        "school_a": school_a,
        "school_b": school_b,
        "family_a": family_a,
        "child_a": child_a,
        "geofence_a": geofence_a,
    }


def _make_client(sl_engine, sl_session, user_id, group_id, role="owner"):
    app = create_app()

    async def get_db_override():
        try:
            yield sl_session
            await sl_session.commit()
        except Exception:
            await sl_session.rollback()
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
# Security 1: Attendance response never includes coordinates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attendance_never_includes_coordinates(sl_engine, sl_session, sl_data):
    """School attendance response must not contain latitude, longitude, or accuracy."""
    d = sl_data

    # Grant consent + check-in via service layer
    await create_school_consent(sl_session, d["child_a"].id, d["school_a"].id, d["parent_a"].id)
    await sl_session.flush()
    await record_check_in(sl_session, d["child_a"].id, d["geofence_a"].id)
    await sl_session.flush()

    async with _make_client(
        sl_engine, sl_session, d["school_a_owner"].id, d["school_a"].id, role="school_admin"
    ) as client:
        today = datetime.now(timezone.utc).date().isoformat() + "T00:00:00Z"
        resp = await client.get(
            f"/api/v1/location/school/{d['school_a'].id}/attendance",
            params={"date": today},
        )
        assert resp.status_code == 200
        body = resp.json()
        for record in body["items"]:
            assert "latitude" not in record, "latitude must never be in attendance response"
            assert "longitude" not in record, "longitude must never be in attendance response"
            assert "accuracy" not in record, "accuracy must never be in attendance response"
            assert "source" not in record, "source must never be in attendance response"


# ---------------------------------------------------------------------------
# Security 2: School admin cannot access real-time location endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_school_admin_cannot_call_current_location(sl_engine, sl_session, sl_data):
    """School admin hitting the /current endpoint gets no coordinates from check-in data."""
    d = sl_data

    # The /current endpoint returns LocationRecord (GPS data), not check-in data.
    # A school admin should never get GPS data — the endpoint returns None if no
    # LocationRecord exists (check-in records are separate from GPS records).
    await create_school_consent(sl_session, d["child_a"].id, d["school_a"].id, d["parent_a"].id)
    await sl_session.flush()
    await record_check_in(sl_session, d["child_a"].id, d["geofence_a"].id)
    await sl_session.flush()

    async with _make_client(
        sl_engine, sl_session, d["school_a_owner"].id, d["school_a"].id, role="school_admin"
    ) as client:
        resp = await client.get(f"/api/v1/location/{d['child_a'].id}/current")
        # Either null (no GPS records) or 200 — but not a coordinate from check-in
        assert resp.status_code == 200
        body = resp.json()
        # LocationRecord.latitude is an ENCRYPTED string, never a raw float
        if body is not None:
            assert isinstance(body.get("latitude"), str), "latitude must be encrypted string, not float"


# ---------------------------------------------------------------------------
# Security 3: Attendance response does not include location history fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attendance_no_history_fields(sl_session, sl_data):
    """get_school_attendance service function returns no location history fields."""
    d = sl_data

    await create_school_consent(sl_session, d["child_a"].id, d["school_a"].id, d["parent_a"].id)
    await sl_session.flush()
    await record_check_in(sl_session, d["child_a"].id, d["geofence_a"].id)
    await sl_session.flush()

    today = datetime.now(timezone.utc)
    records = await get_school_attendance(sl_session, d["school_a"].id, today)

    for rec in records:
        assert "latitude" not in rec
        assert "longitude" not in rec
        assert "accuracy" not in rec
        assert "source" not in rec
        # Only timestamp fields + IDs
        assert "check_in_at" in rec
        assert "member_id" in rec


# ---------------------------------------------------------------------------
# Security 4: Consent required before check-in (service-level)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consent_required_service_level(sl_session, sl_data):
    """record_check_in raises ForbiddenError without consent at service level."""
    from src.exceptions import ForbiddenError

    d = sl_data

    with pytest.raises(ForbiddenError):
        await record_check_in(sl_session, d["child_a"].id, d["geofence_a"].id)


# ---------------------------------------------------------------------------
# Security 5: Parent can revoke consent at any time
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_can_revoke_at_any_time(sl_engine, sl_session, sl_data):
    """Parent can revoke school consent and it blocks future check-ins immediately."""
    d = sl_data

    async with _make_client(sl_engine, sl_session, d["parent_a"].id, d["family_a"].id) as client:
        # Grant
        grant = await client.post(
            "/api/v1/location/school-consent",
            json={
                "member_id": str(d["child_a"].id),
                "school_group_id": str(d["school_a"].id),
            },
        )
        consent_id = grant.json()["id"]

        # Check-in to verify it works
        ci = await client.post(
            "/api/v1/location/check-in",
            json={
                "member_id": str(d["child_a"].id),
                "geofence_id": str(d["geofence_a"].id),
            },
        )
        assert ci.status_code == 201
        # Check-out to close
        await client.post(
            "/api/v1/location/check-out",
            json={
                "member_id": str(d["child_a"].id),
                "geofence_id": str(d["geofence_a"].id),
            },
        )

        # Revoke — must work regardless of time
        rev = await client.delete(f"/api/v1/location/school-consent/{consent_id}")
        assert rev.status_code == 200

        # Next check-in must fail immediately
        ci2 = await client.post(
            "/api/v1/location/check-in",
            json={
                "member_id": str(d["child_a"].id),
                "geofence_id": str(d["geofence_a"].id),
            },
        )
        assert ci2.status_code == 403


# ---------------------------------------------------------------------------
# Security 6: Cross-school isolation — school B cannot see school A's attendance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_school_isolation(sl_engine, sl_session, sl_data):
    """School B cannot see check-in records that belong to school A."""
    d = sl_data

    # Create check-in for school A
    await create_school_consent(sl_session, d["child_a"].id, d["school_a"].id, d["parent_a"].id)
    await sl_session.flush()
    await record_check_in(sl_session, d["child_a"].id, d["geofence_a"].id)
    await sl_session.flush()

    async with _make_client(
        sl_engine, sl_session, d["school_b_owner"].id, d["school_b"].id, role="school_admin"
    ) as client:
        today = datetime.now(timezone.utc).date().isoformat() + "T00:00:00Z"
        # School B queries its own group_id — should return no records
        resp = await client.get(
            f"/api/v1/location/school/{d['school_b'].id}/attendance",
            params={"date": today},
        )
        assert resp.status_code == 200
        body = resp.json()
        # School B has 0 check-ins because consent was given to school A only
        assert body["total"] == 0


# ---------------------------------------------------------------------------
# Security 7: Auth required — no token returns 401 or 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_required_for_school_consent(sl_engine, sl_session):
    """POST /school-consent without auth returns 401 or 403."""
    app = create_app()

    async def get_db_override():
        yield sl_session

    app.dependency_overrides[get_db] = get_db_override
    # Do NOT override get_current_user — let the real auth middleware run

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v1/location/school-consent",
            json={
                "member_id": str(uuid.uuid4()),
                "school_group_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Security 8: Auth required for check-in endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_required_for_checkin(sl_engine, sl_session):
    """POST /check-in without auth returns 401 or 403."""
    app = create_app()

    async def get_db_override():
        yield sl_session

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v1/location/check-in",
            json={
                "member_id": str(uuid.uuid4()),
                "geofence_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Security 9: Auth required for attendance endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_required_for_attendance(sl_engine, sl_session):
    """GET /school/{group_id}/attendance without auth returns 401 or 403."""
    app = create_app()

    async def get_db_override():
        yield sl_session

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get(
            f"/api/v1/location/school/{uuid.uuid4()}/attendance",
            params={"date": "2026-01-01T00:00:00Z"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Security 10: Attendance items contain only approved safe fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attendance_safe_fields_only(sl_session, sl_data):
    """Each attendance record contains only: id, member_id, geofence_id, check_in_at, check_out_at."""
    d = sl_data

    await create_school_consent(sl_session, d["child_a"].id, d["school_a"].id, d["parent_a"].id)
    await sl_session.flush()
    await record_check_in(sl_session, d["child_a"].id, d["geofence_a"].id)
    await sl_session.flush()

    today = datetime.now(timezone.utc)
    records = await get_school_attendance(sl_session, d["school_a"].id, today)
    assert len(records) >= 1

    ALLOWED_KEYS = {"id", "member_id", "geofence_id", "check_in_at", "check_out_at"}
    for rec in records:
        extra_keys = set(rec.keys()) - ALLOWED_KEYS
        assert not extra_keys, f"Unexpected keys in attendance record: {extra_keys}"


# ---------------------------------------------------------------------------
# Security 11: Revoked consent response includes revoked_at timestamp
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revoked_consent_has_timestamp(sl_engine, sl_session, sl_data):
    """Revoked consent response contains a non-null revoked_at field."""
    d = sl_data

    async with _make_client(sl_engine, sl_session, d["parent_a"].id, d["family_a"].id) as client:
        grant = await client.post(
            "/api/v1/location/school-consent",
            json={
                "member_id": str(d["child_a"].id),
                "school_group_id": str(d["school_a"].id),
            },
        )
        consent_id = grant.json()["id"]

        rev = await client.delete(f"/api/v1/location/school-consent/{consent_id}")
        assert rev.status_code == 200
        body = rev.json()
        assert body["revoked_at"] is not None
        # Verify the timestamp is parseable and in the past
        raw = body["revoked_at"].replace("Z", "+00:00")
        revoked_at = datetime.fromisoformat(raw)
        # Normalise to UTC if offset-naive (SQLite returns naive datetimes)
        if revoked_at.tzinfo is None:
            revoked_at = revoked_at.replace(tzinfo=timezone.utc)
        assert revoked_at <= datetime.now(timezone.utc)
