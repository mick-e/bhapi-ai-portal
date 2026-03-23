"""Unit tests for the location module — models and schemas."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.groups.models import Group, GroupMember
from src.location.models import (
    Geofence,
    GeofenceEvent,
    LocationAuditLog,
    LocationKillSwitch,
    LocationRecord,
    LocationSharingConsent,
    SchoolCheckIn,
)
from src.location.schemas import (
    AuditLogListResponse,
    AuditLogResponse,
    GeofenceCreate,
    GeofenceEventResponse,
    GeofenceListResponse,
    GeofenceResponse,
    KillSwitchResponse,
    LocationConsentCreate,
    LocationConsentResponse,
    LocationRecordResponse,
    LocationReportCreate,
    SchoolCheckInResponse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime.now(timezone.utc)


def make_uuid() -> uuid.UUID:
    return uuid.uuid4()


async def _create_user_group_member(session: AsyncSession):
    """Create a User, Group, and GroupMember to satisfy FK constraints."""
    owner_id = make_uuid()
    group_id = make_uuid()
    member_id = make_uuid()

    user = User(
        id=owner_id,
        email=f"loc-{owner_id.hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehash",
        display_name="Location Test",
        account_type="family",
        email_verified=True,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()

    group = Group(
        id=group_id,
        name="Test Family",
        type="family",
        owner_id=owner_id,
        settings={},
    )
    session.add(group)
    await session.flush()

    member = GroupMember(
        id=member_id,
        group_id=group_id,
        user_id=owner_id,
        role="child",
        display_name="Child",
    )
    session.add(member)
    await session.flush()

    return user, group, member


# ---------------------------------------------------------------------------
# Test 1: LocationRecord model instantiation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_location_record_instantiation(test_session: AsyncSession):
    """LocationRecord can be created and queried."""
    user, group, member = await _create_user_group_member(test_session)

    record = LocationRecord(
        id=make_uuid(),
        member_id=member.id,
        group_id=group.id,
        latitude="gAAAAABnYW50ZW5jcnlwdGVkX2xhdA==",  # simulated encrypted value
        longitude="gAAAAABnYW50ZW5jcnlwdGVkX2xvbmc=",
        accuracy=5.0,
        source="gps",
        recorded_at=NOW,
    )
    test_session.add(record)
    await test_session.flush()

    result = await test_session.get(LocationRecord, record.id)
    assert result is not None
    assert result.member_id == member.id
    assert result.group_id == group.id
    assert result.accuracy == 5.0
    assert result.source == "gps"


# ---------------------------------------------------------------------------
# Test 2: Geofence model instantiation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geofence_instantiation(test_session: AsyncSession):
    """Geofence can be created and queried."""
    user, group, member = await _create_user_group_member(test_session)

    fence = Geofence(
        id=make_uuid(),
        group_id=group.id,
        member_id=member.id,
        name="School Zone",
        latitude=51.5074,
        longitude=-0.1278,
        radius_meters=200.0,
        notify_on_enter=True,
        notify_on_exit=True,
    )
    test_session.add(fence)
    await test_session.flush()

    result = await test_session.get(Geofence, fence.id)
    assert result is not None
    assert result.name == "School Zone"
    assert result.radius_meters == 200.0
    assert result.notify_on_enter is True


# ---------------------------------------------------------------------------
# Test 3: GeofenceEvent model instantiation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geofence_event_instantiation(test_session: AsyncSession):
    """GeofenceEvent records enter/exit events."""
    user, group, member = await _create_user_group_member(test_session)

    fence = Geofence(
        id=make_uuid(),
        group_id=group.id,
        member_id=member.id,
        name="Home",
        latitude=40.7128,
        longitude=-74.0060,
        radius_meters=100.0,
    )
    test_session.add(fence)
    await test_session.flush()

    event = GeofenceEvent(
        id=make_uuid(),
        geofence_id=fence.id,
        member_id=member.id,
        event_type="enter",
        recorded_at=NOW,
    )
    test_session.add(event)
    await test_session.flush()

    result = await test_session.get(GeofenceEvent, event.id)
    assert result is not None
    assert result.event_type == "enter"
    assert result.geofence_id == fence.id


# ---------------------------------------------------------------------------
# Test 4: SchoolCheckIn model instantiation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_school_checkin_instantiation(test_session: AsyncSession):
    """SchoolCheckIn records attendance without exposing coordinates."""
    user, group, member = await _create_user_group_member(test_session)

    fence = Geofence(
        id=make_uuid(),
        group_id=group.id,
        member_id=member.id,
        name="School Gate",
        latitude=51.5,
        longitude=-0.1,
        radius_meters=50.0,
    )
    test_session.add(fence)
    await test_session.flush()

    checkin = SchoolCheckIn(
        id=make_uuid(),
        member_id=member.id,
        group_id=group.id,
        geofence_id=fence.id,
        check_in_at=NOW,
        check_out_at=None,
    )
    test_session.add(checkin)
    await test_session.flush()

    result = await test_session.get(SchoolCheckIn, checkin.id)
    assert result is not None
    assert result.check_in_at == NOW
    assert result.check_out_at is None


# ---------------------------------------------------------------------------
# Test 5: LocationSharingConsent unique constraint per member+group
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_location_consent_unique_constraint(test_session: AsyncSession):
    """LocationSharingConsent enforces uniqueness per (member_id, group_id)."""
    user, group, member = await _create_user_group_member(test_session)

    consent1 = LocationSharingConsent(
        id=make_uuid(),
        member_id=member.id,
        group_id=group.id,
        granted_by=user.id,
        granted_at=NOW,
    )
    test_session.add(consent1)
    await test_session.flush()

    # Attempt to insert duplicate (member_id, group_id) — must raise
    consent2 = LocationSharingConsent(
        id=make_uuid(),
        member_id=member.id,
        group_id=group.id,
        granted_by=user.id,
        granted_at=NOW,
    )
    test_session.add(consent2)
    with pytest.raises(IntegrityError):
        await test_session.flush()


# ---------------------------------------------------------------------------
# Test 6: LocationKillSwitch unique constraint per member
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kill_switch_unique_per_member(test_session: AsyncSession):
    """LocationKillSwitch enforces one kill-switch record per member."""
    user, group, member = await _create_user_group_member(test_session)

    ks1 = LocationKillSwitch(
        id=make_uuid(),
        member_id=member.id,
        activated_by=user.id,
        activated_at=NOW,
    )
    test_session.add(ks1)
    await test_session.flush()

    ks2 = LocationKillSwitch(
        id=make_uuid(),
        member_id=member.id,
        activated_by=user.id,
        activated_at=NOW,
    )
    test_session.add(ks2)
    with pytest.raises(IntegrityError):
        await test_session.flush()


# ---------------------------------------------------------------------------
# Test 7: LocationAuditLog model instantiation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_location_audit_log_instantiation(test_session: AsyncSession):
    """LocationAuditLog records every access to location data."""
    user, group, member = await _create_user_group_member(test_session)

    log = LocationAuditLog(
        id=make_uuid(),
        member_id=member.id,
        accessor_id=user.id,
        data_type="current",
        accessed_at=NOW,
    )
    test_session.add(log)
    await test_session.flush()

    result = await test_session.get(LocationAuditLog, log.id)
    assert result is not None
    assert result.data_type == "current"
    assert result.accessor_id == user.id


# ---------------------------------------------------------------------------
# Test 8: LocationReportCreate schema — valid source enum
# ---------------------------------------------------------------------------


def test_location_report_create_valid_sources():
    """LocationReportCreate accepts gps, network, and fused as source values."""
    base = {"member_id": make_uuid(), "latitude": 51.5, "longitude": -0.1, "accuracy": 5.0, "recorded_at": NOW}

    for source in ("gps", "network", "fused"):
        schema = LocationReportCreate(**base, source=source)
        assert schema.source == source


# ---------------------------------------------------------------------------
# Test 9: LocationReportCreate schema — lat/lng range validation
# ---------------------------------------------------------------------------


def test_location_report_lat_lng_ranges():
    """LocationReportCreate validates lat/lng ranges strictly."""
    base_valid = {"member_id": make_uuid(), "accuracy": 5.0, "recorded_at": NOW}

    # Valid boundaries
    schema = LocationReportCreate(**base_valid, latitude=90.0, longitude=180.0)
    assert schema.latitude == 90.0

    # Invalid latitude > 90
    with pytest.raises(PydanticValidationError):
        LocationReportCreate(**base_valid, latitude=91.0, longitude=0.0)

    # Invalid latitude < -90
    with pytest.raises(PydanticValidationError):
        LocationReportCreate(**base_valid, latitude=-91.0, longitude=0.0)

    # Invalid longitude > 180
    with pytest.raises(PydanticValidationError):
        LocationReportCreate(**base_valid, latitude=0.0, longitude=181.0)

    # Invalid longitude < -180
    with pytest.raises(PydanticValidationError):
        LocationReportCreate(**base_valid, latitude=0.0, longitude=-181.0)


# ---------------------------------------------------------------------------
# Test 10: LocationReportCreate schema — invalid source enum
# ---------------------------------------------------------------------------


def test_location_report_invalid_source():
    """LocationReportCreate rejects unknown source values."""
    with pytest.raises(PydanticValidationError):
        LocationReportCreate(
            member_id=make_uuid(),
            latitude=0.0,
            longitude=0.0,
            accuracy=5.0,
            source="cellular",
            recorded_at=NOW,
        )


# ---------------------------------------------------------------------------
# Test 11: GeofenceCreate schema — radius validation
# ---------------------------------------------------------------------------


def test_geofence_create_radius_validation():
    """GeofenceCreate rejects zero and negative radius values."""
    base = {"member_id": make_uuid(), "name": "Home", "latitude": 0.0, "longitude": 0.0}

    # Valid radius
    schema = GeofenceCreate(**base, radius_meters=500.0)
    assert schema.radius_meters == 500.0

    # Zero radius is invalid
    with pytest.raises(PydanticValidationError):
        GeofenceCreate(**base, radius_meters=0.0)

    # Negative radius is invalid
    with pytest.raises(PydanticValidationError):
        GeofenceCreate(**base, radius_meters=-100.0)

    # Max radius boundary (50km)
    schema_max = GeofenceCreate(**base, radius_meters=50000.0)
    assert schema_max.radius_meters == 50000.0

    # Exceeds max radius
    with pytest.raises(PydanticValidationError):
        GeofenceCreate(**base, radius_meters=50001.0)


# ---------------------------------------------------------------------------
# Test 12: GeofenceCreate schema — name length validation
# ---------------------------------------------------------------------------


def test_geofence_create_name_validation():
    """GeofenceCreate enforces name length constraints."""
    base = {"member_id": make_uuid(), "latitude": 0.0, "longitude": 0.0, "radius_meters": 100.0}

    # Empty name rejected
    with pytest.raises(PydanticValidationError):
        GeofenceCreate(**base, name="")

    # Max length (100 chars) is valid
    schema = GeofenceCreate(**base, name="A" * 100)
    assert len(schema.name) == 100

    # Over max length rejected
    with pytest.raises(PydanticValidationError):
        GeofenceCreate(**base, name="A" * 101)


# ---------------------------------------------------------------------------
# Test 13: GeofenceEventResponse schema — valid event_type values
# ---------------------------------------------------------------------------


def test_geofence_event_response_schema():
    """GeofenceEventResponse correctly represents enter and exit events."""
    for event_type in ("enter", "exit"):
        response = GeofenceEventResponse(
            id=make_uuid(),
            geofence_id=make_uuid(),
            member_id=make_uuid(),
            event_type=event_type,
            recorded_at=NOW,
            created_at=NOW,
        )
        assert response.event_type == event_type


# ---------------------------------------------------------------------------
# Test 14: KillSwitchResponse.is_active property
# ---------------------------------------------------------------------------


def test_kill_switch_response_is_active():
    """KillSwitchResponse.is_active reflects whether deactivated_at is None."""
    active_ks = KillSwitchResponse(
        id=make_uuid(),
        member_id=make_uuid(),
        activated_by=make_uuid(),
        activated_at=NOW,
        deactivated_at=None,
        created_at=NOW,
    )
    assert active_ks.is_active is True

    from datetime import timedelta
    deactivated_ks = KillSwitchResponse(
        id=make_uuid(),
        member_id=make_uuid(),
        activated_by=make_uuid(),
        activated_at=NOW,
        deactivated_at=NOW + timedelta(hours=1),
        created_at=NOW,
    )
    assert deactivated_ks.is_active is False


# ---------------------------------------------------------------------------
# Test 15: AuditLogListResponse pagination schema
# ---------------------------------------------------------------------------


def test_audit_log_list_response_pagination():
    """AuditLogListResponse correctly structures paginated data."""
    entry = AuditLogResponse(
        id=make_uuid(),
        member_id=make_uuid(),
        accessor_id=make_uuid(),
        data_type="history",
        accessed_at=NOW,
        created_at=NOW,
    )
    response = AuditLogListResponse(
        items=[entry],
        total=42,
        offset=0,
        limit=10,
        has_more=True,
    )
    assert response.total == 42
    assert response.has_more is True
    assert len(response.items) == 1
    assert response.items[0].data_type == "history"
