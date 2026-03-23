"""Unit tests for the location service module."""

import math
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.exceptions import NotFoundError, ValidationError
from src.groups.models import Group, GroupMember
from src.location.models import (
    Geofence,
    GeofenceEvent,
    LocationAuditLog,
    LocationKillSwitch,
    LocationRecord,
    SchoolCheckIn,
)
from src.location.service import (
    activate_kill_switch,
    check_geofence,
    create_geofence,
    deactivate_kill_switch,
    delete_geofence,
    delete_location_history,
    get_audit_log,
    get_current_location,
    get_kill_switch_status,
    get_location_history,
    haversine_distance,
    list_geofences,
    purge_expired_locations,
    report_location,
)

NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def loc_data(test_session: AsyncSession):
    """Create user, group, and member for location tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"loc-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Location Parent",
        account_type="family",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Location Family",
        type="family",
        owner_id=user.id,
        settings={},
    )
    test_session.add(group)
    await test_session.flush()

    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="child",
        display_name="Location Child",
    )
    test_session.add(member)
    await test_session.flush()

    return {"user": user, "group": group, "member": member}


# ---------------------------------------------------------------------------
# Test 1: haversine_distance — same point
# ---------------------------------------------------------------------------


def test_haversine_same_point():
    """Distance between identical coordinates is zero."""
    d = haversine_distance(51.5, -0.1, 51.5, -0.1)
    assert d == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Test 2: haversine_distance — known distance (London to Paris ~341 km)
# ---------------------------------------------------------------------------


def test_haversine_london_to_paris():
    """Haversine distance between London and Paris is approximately 341 km."""
    # London: 51.5074, -0.1278 | Paris: 48.8566, 2.3522
    d = haversine_distance(51.5074, -0.1278, 48.8566, 2.3522)
    # Allow 5 km tolerance
    assert 335_000 < d < 350_000


# ---------------------------------------------------------------------------
# Test 3: haversine_distance — short distance (100m)
# ---------------------------------------------------------------------------


def test_haversine_short_distance():
    """Haversine correctly calculates distances of ~100 meters."""
    # Move ~0.001 degrees north (~111 meters)
    d = haversine_distance(51.5, 0.0, 51.501, 0.0)
    assert 100 < d < 120


# ---------------------------------------------------------------------------
# Test 4: report_location — encrypted storage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_location_encrypts_coordinates(test_session: AsyncSession, loc_data):
    """report_location stores encrypted lat/lng strings, not plain floats."""
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        record = await report_location(
            test_session,
            member_id=loc_data["member"].id,
            group_id=loc_data["group"].id,
            lat=51.5074,
            lng=-0.1278,
            accuracy=10.0,
            source="gps",
        )

    assert record is not None
    # Stored latitude must be an encrypted string, not the plain float
    assert record.latitude != "51.5074"
    assert isinstance(record.latitude, str)
    assert len(record.latitude) > 10  # encrypted token is longer than the plain value
    assert record.longitude != "-0.1278"


# ---------------------------------------------------------------------------
# Test 5: report_location — kill switch blocks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_location_kill_switch_blocks(test_session: AsyncSession, loc_data):
    """report_location returns None silently when kill switch is active."""
    await activate_kill_switch(test_session, member_id=loc_data["member"].id, parent_id=loc_data["user"].id)

    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        result = await report_location(
            test_session,
            member_id=loc_data["member"].id,
            group_id=loc_data["group"].id,
            lat=51.0,
            lng=-0.1,
            accuracy=5.0,
            source="gps",
        )

    assert result is None


# ---------------------------------------------------------------------------
# Test 6: report_location — kill switch deactivated allows reporting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_location_after_kill_switch_deactivated(test_session: AsyncSession, loc_data):
    """After kill switch is deactivated, reporting works again."""
    await activate_kill_switch(test_session, member_id=loc_data["member"].id, parent_id=loc_data["user"].id)
    await deactivate_kill_switch(test_session, member_id=loc_data["member"].id, parent_id=loc_data["user"].id)

    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        record = await report_location(
            test_session,
            member_id=loc_data["member"].id,
            group_id=loc_data["group"].id,
            lat=51.0,
            lng=-0.1,
            accuracy=5.0,
            source="gps",
        )

    assert record is not None
    assert record.member_id == loc_data["member"].id


# ---------------------------------------------------------------------------
# Test 7: get_current_location — creates audit log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_location_creates_audit_log(test_session: AsyncSession, loc_data):
    """get_current_location creates an audit log entry on every call."""
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        await report_location(
            test_session,
            member_id=loc_data["member"].id,
            group_id=loc_data["group"].id,
            lat=40.7128,
            lng=-74.0060,
            accuracy=8.0,
            source="gps",
        )

    await get_current_location(
        test_session,
        member_id=loc_data["member"].id,
        accessor_id=loc_data["user"].id,
    )

    from sqlalchemy import select
    result = await test_session.execute(
        select(LocationAuditLog).where(
            LocationAuditLog.member_id == loc_data["member"].id,
            LocationAuditLog.data_type == "current",
        )
    )
    logs = result.scalars().all()
    assert len(logs) >= 1


# ---------------------------------------------------------------------------
# Test 8: get_current_location — decrypts coordinates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_location_decrypts(test_session: AsyncSession, loc_data):
    """get_current_location returns decrypted float coordinates."""
    expected_lat, expected_lng = 40.7128, -74.0060

    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        await report_location(
            test_session,
            member_id=loc_data["member"].id,
            group_id=loc_data["group"].id,
            lat=expected_lat,
            lng=expected_lng,
            accuracy=8.0,
            source="gps",
        )

    location = await get_current_location(
        test_session,
        member_id=loc_data["member"].id,
        accessor_id=loc_data["user"].id,
    )

    assert location is not None
    assert location["latitude"] == pytest.approx(expected_lat)
    assert location["longitude"] == pytest.approx(expected_lng)


# ---------------------------------------------------------------------------
# Test 9: get_current_location — returns None when no records
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_location_none_when_empty(test_session: AsyncSession, loc_data):
    """get_current_location returns None if no location data exists."""
    result = await get_current_location(
        test_session,
        member_id=loc_data["member"].id,
        accessor_id=loc_data["user"].id,
    )
    assert result is None


# ---------------------------------------------------------------------------
# Test 10: get_location_history — creates audit log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_location_history_creates_audit_log(test_session: AsyncSession, loc_data):
    """get_location_history creates an audit log entry."""
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        await report_location(
            test_session,
            member_id=loc_data["member"].id,
            group_id=loc_data["group"].id,
            lat=51.0,
            lng=-0.1,
            accuracy=5.0,
            source="gps",
        )

    await get_location_history(
        test_session,
        member_id=loc_data["member"].id,
        accessor_id=loc_data["user"].id,
    )

    from sqlalchemy import select
    result = await test_session.execute(
        select(LocationAuditLog).where(
            LocationAuditLog.member_id == loc_data["member"].id,
            LocationAuditLog.data_type == "history",
        )
    )
    logs = result.scalars().all()
    assert len(logs) >= 1


# ---------------------------------------------------------------------------
# Test 11: get_location_history — enforces 30-day max window
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_location_history_max_30_days(test_session: AsyncSession, loc_data):
    """get_location_history ignores data older than 30 days."""
    old_time = datetime.now(timezone.utc) - timedelta(days=45)
    # Insert an old record directly
    old_record = LocationRecord(
        id=uuid.uuid4(),
        member_id=loc_data["member"].id,
        group_id=loc_data["group"].id,
        latitude="gAAAAABfakeencryptedlat==",
        longitude="gAAAAABfakeencryptedlng==",
        accuracy=5.0,
        source="gps",
        recorded_at=old_time,
    )
    test_session.add(old_record)
    await test_session.flush()

    # Pass start_date older than 30 days — should be clamped
    very_old_start = datetime.now(timezone.utc) - timedelta(days=60)
    items, total = await get_location_history(
        test_session,
        member_id=loc_data["member"].id,
        accessor_id=loc_data["user"].id,
        start_date=very_old_start,
    )

    # The 45-day-old record should not appear
    record_ids = [item["id"] for item in items]
    assert old_record.id not in record_ids


# ---------------------------------------------------------------------------
# Test 12: create_geofence — max 10 limit enforced
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_geofence_max_limit(test_session: AsyncSession, loc_data):
    """create_geofence raises ValidationError after 10 geofences."""
    for i in range(10):
        await create_geofence(
            test_session,
            group_id=loc_data["group"].id,
            member_id=loc_data["member"].id,
            name=f"Geofence {i}",
            lat=51.5 + i * 0.01,
            lng=-0.1,
            radius=100.0,
        )
    await test_session.flush()

    with pytest.raises(ValidationError, match="Maximum of 10 geofences"):
        await create_geofence(
            test_session,
            group_id=loc_data["group"].id,
            member_id=loc_data["member"].id,
            name="Geofence 11",
            lat=52.0,
            lng=-0.1,
            radius=100.0,
        )


# ---------------------------------------------------------------------------
# Test 13: create_geofence — below limit succeeds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_geofence_succeeds(test_session: AsyncSession, loc_data):
    """create_geofence returns a Geofence object when below the limit."""
    fence = await create_geofence(
        test_session,
        group_id=loc_data["group"].id,
        member_id=loc_data["member"].id,
        name="School",
        lat=51.5,
        lng=-0.1,
        radius=200.0,
    )
    assert fence.id is not None
    assert fence.name == "School"
    assert fence.radius_meters == 200.0


# ---------------------------------------------------------------------------
# Test 14: check_geofence — inside boundary triggers enter event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_geofence_inside_boundary(test_session: AsyncSession, loc_data):
    """check_geofence detects when a child is inside a geofence."""
    fence = await create_geofence(
        test_session,
        group_id=loc_data["group"].id,
        member_id=loc_data["member"].id,
        name="Home",
        lat=51.5,
        lng=-0.1,
        radius=500.0,
    )
    await test_session.flush()

    # Position exactly at the center — definitely inside
    triggered = await check_geofence(
        test_session,
        member_id=loc_data["member"].id,
        lat=51.5,
        lng=-0.1,
    )

    assert len(triggered) == 1
    assert triggered[0]["geofence_id"] == fence.id
    assert triggered[0]["event_type"] == "enter"


# ---------------------------------------------------------------------------
# Test 15: check_geofence — outside boundary not triggered
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_geofence_outside_boundary(test_session: AsyncSession, loc_data):
    """check_geofence returns empty list when child is outside all geofences."""
    await create_geofence(
        test_session,
        group_id=loc_data["group"].id,
        member_id=loc_data["member"].id,
        name="School",
        lat=51.5,
        lng=-0.1,
        radius=50.0,  # Small 50m radius
    )
    await test_session.flush()

    # Position ~1 km away — definitely outside
    triggered = await check_geofence(
        test_session,
        member_id=loc_data["member"].id,
        lat=51.51,
        lng=-0.1,  # ~1.1 km north
    )

    assert len(triggered) == 0


# ---------------------------------------------------------------------------
# Test 16: kill switch activate and deactivate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kill_switch_activate_deactivate(test_session: AsyncSession, loc_data):
    """Kill switch can be activated and deactivated."""
    ks = await activate_kill_switch(
        test_session, member_id=loc_data["member"].id, parent_id=loc_data["user"].id
    )
    assert ks.deactivated_at is None

    ks = await deactivate_kill_switch(
        test_session, member_id=loc_data["member"].id, parent_id=loc_data["user"].id
    )
    assert ks.deactivated_at is not None


# ---------------------------------------------------------------------------
# Test 17: kill switch status — None when never set
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kill_switch_status_none_when_not_set(test_session: AsyncSession, loc_data):
    """get_kill_switch_status returns None if no kill switch record exists."""
    result = await get_kill_switch_status(test_session, member_id=loc_data["member"].id)
    assert result is None


# ---------------------------------------------------------------------------
# Test 18: delete_location_history — GDPR erasure completeness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_erasure_deletes_all_records(test_session: AsyncSession, loc_data):
    """delete_location_history removes all LocationRecords for the member."""
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        for _ in range(3):
            await report_location(
                test_session,
                member_id=loc_data["member"].id,
                group_id=loc_data["group"].id,
                lat=51.5,
                lng=-0.1,
                accuracy=5.0,
                source="gps",
            )
    await test_session.flush()

    result = await delete_location_history(test_session, member_id=loc_data["member"].id)
    await test_session.flush()

    assert result["records_deleted"] == 3
    assert result["status"] == "erased"

    # Verify no records remain
    from sqlalchemy import select
    remaining = await test_session.execute(
        select(LocationRecord).where(LocationRecord.member_id == loc_data["member"].id)
    )
    assert remaining.scalars().first() is None


# ---------------------------------------------------------------------------
# Test 19: delete_location_history — also removes SchoolCheckIns
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_erasure_removes_school_checkins(test_session: AsyncSession, loc_data):
    """delete_location_history also deletes SchoolCheckIn records."""
    fence = Geofence(
        id=uuid.uuid4(),
        group_id=loc_data["group"].id,
        member_id=loc_data["member"].id,
        name="School",
        latitude=51.5,
        longitude=-0.1,
        radius_meters=100.0,
    )
    test_session.add(fence)
    await test_session.flush()

    checkin = SchoolCheckIn(
        id=uuid.uuid4(),
        member_id=loc_data["member"].id,
        group_id=loc_data["group"].id,
        geofence_id=fence.id,
        check_in_at=NOW,
    )
    test_session.add(checkin)
    await test_session.flush()

    result = await delete_location_history(test_session, member_id=loc_data["member"].id)
    await test_session.flush()

    assert result["checkins_deleted"] == 1

    from sqlalchemy import select
    remaining = await test_session.execute(
        select(SchoolCheckIn).where(SchoolCheckIn.member_id == loc_data["member"].id)
    )
    assert remaining.scalars().first() is None


# ---------------------------------------------------------------------------
# Test 20: purge_expired_locations — removes records older than 30 days
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purge_expired_locations(test_session: AsyncSession, loc_data):
    """purge_expired_locations deletes records older than 30 days."""
    old_time = datetime.now(timezone.utc) - timedelta(days=35)
    recent_time = datetime.now(timezone.utc) - timedelta(days=5)

    old_record = LocationRecord(
        id=uuid.uuid4(),
        member_id=loc_data["member"].id,
        group_id=loc_data["group"].id,
        latitude="enc_lat",
        longitude="enc_lng",
        accuracy=5.0,
        source="gps",
        recorded_at=old_time,
    )
    recent_record = LocationRecord(
        id=uuid.uuid4(),
        member_id=loc_data["member"].id,
        group_id=loc_data["group"].id,
        latitude="enc_lat2",
        longitude="enc_lng2",
        accuracy=5.0,
        source="gps",
        recorded_at=recent_time,
    )
    test_session.add_all([old_record, recent_record])
    await test_session.flush()

    deleted = await purge_expired_locations(test_session)
    await test_session.flush()

    assert deleted >= 1

    # Recent record should still exist
    from sqlalchemy import select
    remaining = await test_session.execute(
        select(LocationRecord).where(LocationRecord.id == recent_record.id)
    )
    assert remaining.scalar_one_or_none() is not None

    # Old record should be gone
    old_remaining = await test_session.execute(
        select(LocationRecord).where(LocationRecord.id == old_record.id)
    )
    assert old_remaining.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# Test 21: list_geofences — returns all fences for member
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_geofences(test_session: AsyncSession, loc_data):
    """list_geofences returns all geofences for a member."""
    for i in range(3):
        await create_geofence(
            test_session,
            group_id=loc_data["group"].id,
            member_id=loc_data["member"].id,
            name=f"Zone {i}",
            lat=51.5 + i * 0.01,
            lng=-0.1,
            radius=100.0,
        )
    await test_session.flush()

    fences = await list_geofences(
        test_session, group_id=loc_data["group"].id, member_id=loc_data["member"].id
    )
    assert len(fences) == 3


# ---------------------------------------------------------------------------
# Test 22: delete_geofence — raises NotFoundError for unknown ID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_geofence_not_found(test_session: AsyncSession):
    """delete_geofence raises NotFoundError for an unknown geofence ID."""
    with pytest.raises(NotFoundError):
        await delete_geofence(test_session, geofence_id=uuid.uuid4())


# ---------------------------------------------------------------------------
# Test 23: get_audit_log — paginated retrieval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_audit_log_paginated(test_session: AsyncSession, loc_data):
    """get_audit_log returns paginated audit entries."""
    with patch("src.location.service.publish_event", new_callable=AsyncMock):
        await report_location(
            test_session,
            member_id=loc_data["member"].id,
            group_id=loc_data["group"].id,
            lat=51.5,
            lng=-0.1,
            accuracy=5.0,
            source="gps",
        )

    # Access current location 3 times to generate 3 audit entries
    for _ in range(3):
        await get_current_location(
            test_session,
            member_id=loc_data["member"].id,
            accessor_id=loc_data["user"].id,
        )

    items, total = await get_audit_log(
        test_session, member_id=loc_data["member"].id, offset=0, limit=2
    )
    assert total == 3
    assert len(items) == 2


# ---------------------------------------------------------------------------
# Test 24: check_geofence — multiple fences, only one triggered
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_geofence_multiple_only_one_triggered(test_session: AsyncSession, loc_data):
    """check_geofence correctly identifies which fence is triggered."""
    # Fence at origin (inside)
    fence1 = await create_geofence(
        test_session,
        group_id=loc_data["group"].id,
        member_id=loc_data["member"].id,
        name="Near",
        lat=51.5,
        lng=-0.1,
        radius=500.0,
    )
    # Fence far away (outside)
    await create_geofence(
        test_session,
        group_id=loc_data["group"].id,
        member_id=loc_data["member"].id,
        name="Far",
        lat=48.8566,  # Paris
        lng=2.3522,
        radius=500.0,
    )
    await test_session.flush()

    triggered = await check_geofence(
        test_session,
        member_id=loc_data["member"].id,
        lat=51.5,
        lng=-0.1,
    )

    assert len(triggered) == 1
    assert triggered[0]["geofence_id"] == fence1.id
    assert triggered[0]["geofence_name"] == "Near"
