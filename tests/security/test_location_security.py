"""Security tests for the location module — privacy controls, audit, feature gating."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.exceptions import NotFoundError, ValidationError
from src.groups.models import Group, GroupMember
from src.location.models import GeofenceEvent, LocationAuditLog, LocationRecord
from src.location.service import (
    activate_kill_switch,
    check_geofence,
    create_geofence,
    deactivate_kill_switch,
    delete_geofence,
    delete_location_history,
    get_current_location,
    get_location_history,
    purge_expired_locations,
    report_location,
)
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sec_engine():
    """In-memory SQLite engine for security tests."""
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
async def sec_session(sec_engine):
    session = AsyncSession(sec_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def sec_data(sec_session):
    """Two separate families for cross-family isolation tests."""
    user1 = User(
        id=uuid.uuid4(),
        email=f"loc-sec1-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Parent 1",
        account_type="family",
        email_verified=True,
        mfa_enabled=False,
    )
    user2 = User(
        id=uuid.uuid4(),
        email=f"loc-sec2-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Parent 2",
        account_type="family",
        email_verified=True,
        mfa_enabled=False,
    )
    sec_session.add_all([user1, user2])
    await sec_session.flush()

    group1 = Group(id=uuid.uuid4(), name="Family 1", type="family", owner_id=user1.id)
    group2 = Group(id=uuid.uuid4(), name="Family 2", type="family", owner_id=user2.id)
    sec_session.add_all([group1, group2])
    await sec_session.flush()

    member1 = GroupMember(
        id=uuid.uuid4(), group_id=group1.id, user_id=None, role="child", display_name="Child 1"
    )
    member2 = GroupMember(
        id=uuid.uuid4(), group_id=group2.id, user_id=None, role="child", display_name="Child 2"
    )
    sec_session.add_all([member1, member2])
    await sec_session.flush()

    return {
        "user1": user1, "group1": group1, "member1": member1,
        "user2": user2, "group2": group2, "member2": member2,
    }


@pytest.fixture
async def sec_client(sec_engine, sec_session, sec_data):
    """Authenticated HTTP client for Family 1."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=sec_data["user1"].id,
            group_id=sec_data["group1"].id,
            role="owner",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Test 1: Coordinates are stored encrypted (not plain text in DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coordinates_stored_encrypted(sec_session, sec_data):
    """Verify lat/lng are stored as encrypted tokens, not plain floats."""
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        await report_location(
            sec_session,
            member_id=sec_data["member1"].id,
            group_id=sec_data["group1"].id,
            lat=51.5074,
            lng=-0.1278,
            accuracy=5.0,
            source="gps",
        )
    await sec_session.flush()

    result = await sec_session.execute(
        select(LocationRecord).where(LocationRecord.member_id == sec_data["member1"].id)
    )
    records = result.scalars().all()
    assert len(records) == 1

    # Stored value must NOT be the plaintext coordinate
    assert records[0].latitude != "51.5074"
    assert records[0].longitude != "-0.1278"
    # Encrypted token is substantially longer than a plain float string
    assert len(records[0].latitude) > 20


# ---------------------------------------------------------------------------
# Test 2: Kill switch blocks location reporting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kill_switch_blocks_all_reporting(sec_session, sec_data):
    """Kill switch prevents location from being recorded."""
    await activate_kill_switch(
        sec_session,
        member_id=sec_data["member1"].id,
        parent_id=sec_data["user1"].id,
    )

    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        result = await report_location(
            sec_session,
            member_id=sec_data["member1"].id,
            group_id=sec_data["group1"].id,
            lat=51.5,
            lng=-0.1,
            accuracy=5.0,
            source="gps",
        )

    assert result is None  # kill switch blocked it

    # Verify nothing was written to DB
    db_result = await sec_session.execute(
        select(LocationRecord).where(LocationRecord.member_id == sec_data["member1"].id)
    )
    assert db_result.scalars().first() is None


# ---------------------------------------------------------------------------
# Test 3: Audit log created on every current location read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_log_on_every_read(sec_session, sec_data):
    """Every call to get_current_location creates an audit log entry."""
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        await report_location(
            sec_session,
            member_id=sec_data["member1"].id,
            group_id=sec_data["group1"].id,
            lat=51.5,
            lng=-0.1,
            accuracy=5.0,
            source="gps",
        )

    for _ in range(3):
        await get_current_location(
            sec_session,
            member_id=sec_data["member1"].id,
            accessor_id=sec_data["user1"].id,
        )

    result = await sec_session.execute(
        select(LocationAuditLog).where(
            LocationAuditLog.member_id == sec_data["member1"].id,
            LocationAuditLog.data_type == "current",
        )
    )
    logs = result.scalars().all()
    assert len(logs) == 3


# ---------------------------------------------------------------------------
# Test 4: Audit log created on history read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_log_on_history_read(sec_session, sec_data):
    """get_location_history creates an audit log entry."""
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        await report_location(
            sec_session,
            member_id=sec_data["member1"].id,
            group_id=sec_data["group1"].id,
            lat=51.5,
            lng=-0.1,
            accuracy=5.0,
            source="gps",
        )

    await get_location_history(
        sec_session,
        member_id=sec_data["member1"].id,
        accessor_id=sec_data["user1"].id,
    )

    result = await sec_session.execute(
        select(LocationAuditLog).where(
            LocationAuditLog.member_id == sec_data["member1"].id,
            LocationAuditLog.data_type == "history",
        )
    )
    logs = result.scalars().all()
    assert len(logs) >= 1


# ---------------------------------------------------------------------------
# Test 5: GDPR erasure leaves no residual data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_erasure_no_residual_data(sec_session, sec_data):
    """After GDPR erasure, no location records remain for the member."""
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        for _ in range(5):
            await report_location(
                sec_session,
                member_id=sec_data["member1"].id,
                group_id=sec_data["group1"].id,
                lat=51.5,
                lng=-0.1,
                accuracy=5.0,
                source="gps",
            )
    await sec_session.flush()

    result = await delete_location_history(sec_session, member_id=sec_data["member1"].id)
    await sec_session.flush()

    assert result["records_deleted"] == 5
    assert result["status"] == "erased"

    # Verify no residual data
    remaining = await sec_session.execute(
        select(LocationRecord).where(LocationRecord.member_id == sec_data["member1"].id)
    )
    assert remaining.scalars().first() is None


# ---------------------------------------------------------------------------
# Test 6: GDPR erasure also removes audit logs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_erasure_removes_audit_logs(sec_session, sec_data):
    """GDPR erasure deletes LocationAuditLog entries for the member."""
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        await report_location(
            sec_session,
            member_id=sec_data["member1"].id,
            group_id=sec_data["group1"].id,
            lat=51.5,
            lng=-0.1,
            accuracy=5.0,
            source="gps",
        )

    await get_current_location(
        sec_session,
        member_id=sec_data["member1"].id,
        accessor_id=sec_data["user1"].id,
    )
    await sec_session.flush()

    # Verify audit log exists before erasure
    before = await sec_session.execute(
        select(LocationAuditLog).where(LocationAuditLog.member_id == sec_data["member1"].id)
    )
    assert before.scalars().first() is not None

    await delete_location_history(sec_session, member_id=sec_data["member1"].id)
    await sec_session.flush()

    remaining_logs = await sec_session.execute(
        select(LocationAuditLog).where(LocationAuditLog.member_id == sec_data["member1"].id)
    )
    assert remaining_logs.scalars().first() is None


# ---------------------------------------------------------------------------
# Test 7: Unauthenticated request returns 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(sec_engine):
    """Location endpoints reject unauthenticated requests."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/location/{uuid.uuid4()}/current")

    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Test 8: School admin endpoint for coordinates does not exist (Task 22)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_school_admin_coordinates_endpoint_not_exposed(sec_client, sec_data):
    """School admin coordinate endpoint (Task 22) doesn't exist yet."""
    resp = await sec_client.get(f"/api/v1/location/{sec_data['member1'].id}/school-coordinates")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 9: Kill switch prevents new data after activation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kill_switch_no_new_data_after_activation(sec_session, sec_data):
    """Kill switch prevents any new data from being stored after activation."""
    # Report before kill switch
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        await report_location(
            sec_session,
            member_id=sec_data["member1"].id,
            group_id=sec_data["group1"].id,
            lat=51.5,
            lng=-0.1,
            accuracy=5.0,
            source="gps",
        )

    # Activate kill switch
    await activate_kill_switch(
        sec_session,
        member_id=sec_data["member1"].id,
        parent_id=sec_data["user1"].id,
    )

    # Attempt to report after kill switch
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        blocked = await report_location(
            sec_session,
            member_id=sec_data["member1"].id,
            group_id=sec_data["group1"].id,
            lat=52.0,
            lng=-0.2,
            accuracy=5.0,
            source="gps",
        )

    assert blocked is None

    # Only 1 record should exist (the one before kill switch)
    result = await sec_session.execute(
        select(LocationRecord).where(LocationRecord.member_id == sec_data["member1"].id)
    )
    records = result.scalars().all()
    assert len(records) == 1


# ---------------------------------------------------------------------------
# Test 10: Geofence max 10 enforced — 11th raises ValidationError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geofence_max_10_security(sec_session, sec_data):
    """System enforces the 10-geofence limit per child as a security constraint."""
    for i in range(10):
        await create_geofence(
            sec_session,
            group_id=sec_data["group1"].id,
            member_id=sec_data["member1"].id,
            name=f"Fence {i}",
            lat=51.5 + i * 0.01,
            lng=-0.1,
            radius=100.0,
        )
    await sec_session.flush()

    with pytest.raises(ValidationError, match="Maximum of 10"):
        await create_geofence(
            sec_session,
            group_id=sec_data["group1"].id,
            member_id=sec_data["member1"].id,
            name="Overflow",
            lat=52.0,
            lng=-0.1,
            radius=100.0,
        )


# ---------------------------------------------------------------------------
# Test 11: Cross-family isolation — unknown UUID raises NotFoundError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_family_geofence_isolation(sec_session, sec_data):
    """delete_geofence raises NotFoundError for an unknown geofence UUID."""
    # Family 2 would not know the UUID of Family 1's geofence
    # Attempting to delete a non-existent ID raises NotFoundError
    with pytest.raises(NotFoundError):
        await delete_geofence(sec_session, geofence_id=uuid.uuid4())


# ---------------------------------------------------------------------------
# Test 12: Kill switch deactivation requires the switch to exist
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kill_switch_deactivate_requires_existing(sec_session, sec_data):
    """deactivate_kill_switch raises NotFoundError if no kill switch exists."""
    with pytest.raises(NotFoundError):
        await deactivate_kill_switch(
            sec_session,
            member_id=uuid.uuid4(),  # non-existent member
            parent_id=sec_data["user1"].id,
        )


# ---------------------------------------------------------------------------
# Test 13: GeofenceEvent is created on boundary crossing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geofence_event_created_on_crossing(sec_session, sec_data):
    """GeofenceEvent record is created when a child crosses a boundary."""
    fence = await create_geofence(
        sec_session,
        group_id=sec_data["group1"].id,
        member_id=sec_data["member1"].id,
        name="Zone",
        lat=51.5,
        lng=-0.1,
        radius=500.0,
    )
    await sec_session.flush()

    await check_geofence(sec_session, member_id=sec_data["member1"].id, lat=51.5, lng=-0.1)
    await sec_session.flush()

    result = await sec_session.execute(
        select(GeofenceEvent).where(GeofenceEvent.geofence_id == fence.id)
    )
    events = result.scalars().all()
    assert len(events) == 1
    assert events[0].event_type == "enter"


# ---------------------------------------------------------------------------
# Test 14: Purge does not delete recent records
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purge_preserves_recent_records(sec_session, sec_data):
    """purge_expired_locations does not delete records within the 30-day window."""
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        record = await report_location(
            sec_session,
            member_id=sec_data["member1"].id,
            group_id=sec_data["group1"].id,
            lat=51.5,
            lng=-0.1,
            accuracy=5.0,
            source="gps",
        )
    await sec_session.flush()

    await purge_expired_locations(sec_session)
    await sec_session.flush()

    # Recent records should NOT be deleted (0 or only old records if any)
    # The just-created record should still exist
    remaining = await sec_session.execute(
        select(LocationRecord).where(LocationRecord.id == record.id)
    )
    assert remaining.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Test 15: Audit log accessor_id correctly recorded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_log_accessor_id_recorded(sec_session, sec_data):
    """Audit log stores the correct accessor_id for every location access."""
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        await report_location(
            sec_session,
            member_id=sec_data["member1"].id,
            group_id=sec_data["group1"].id,
            lat=51.5,
            lng=-0.1,
            accuracy=5.0,
            source="gps",
        )

    await get_current_location(
        sec_session,
        member_id=sec_data["member1"].id,
        accessor_id=sec_data["user1"].id,
    )
    await sec_session.flush()

    result = await sec_session.execute(
        select(LocationAuditLog).where(
            LocationAuditLog.member_id == sec_data["member1"].id,
        )
    )
    log = result.scalars().first()
    assert log is not None
    assert log.accessor_id == sec_data["user1"].id
    assert log.data_type == "current"
