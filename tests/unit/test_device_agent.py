"""Unit tests for the device agent module."""

import uuid
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.device_agent.models import AppUsageRecord, DeviceSession, ScreenTimeRecord
from src.device_agent.schemas import (
    AppUsageCreate,
    DeviceSessionCreate,
    DeviceSyncRequest,
)
from src.device_agent.service import (
    get_app_usage_history,
    get_screen_time_summary,
    record_app_usage,
    record_device_session,
    sync_device_data,
    update_screen_time,
)
from src.exceptions import NotFoundError
from src.groups.models import Group, GroupMember

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def device_data(test_session: AsyncSession):
    """Create a group with a member for device agent tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Test Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Test Family",
        type="family",
        owner_id=user.id,
    )
    test_session.add(group)
    await test_session.flush()

    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Child",
        date_of_birth=datetime(2016, 5, 15, tzinfo=timezone.utc),
    )
    test_session.add(member)
    await test_session.flush()

    return {"group": group, "member": member, "user": user}


# ---------------------------------------------------------------------------
# Device Session Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_device_session(test_session: AsyncSession, device_data):
    """Record a device session."""
    data = DeviceSessionCreate(
        member_id=device_data["member"].id,
        device_id="device-abc-123",
        device_type="ios",
        os_version="18.3",
        app_version="1.0.0",
        started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
        battery_level=85.0,
    )
    session = await record_device_session(test_session, device_data["group"].id, data)
    assert session.id is not None
    assert session.device_id == "device-abc-123"
    assert session.device_type == "ios"
    assert session.os_version == "18.3"
    assert session.battery_level == 85.0


@pytest.mark.asyncio
async def test_record_device_session_android(test_session: AsyncSession, device_data):
    """Record an Android device session."""
    data = DeviceSessionCreate(
        member_id=device_data["member"].id,
        device_id="android-xyz",
        device_type="android",
        os_version="15",
        app_version="1.0.0",
        started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 21, 12, 0, 0, tzinfo=timezone.utc),
    )
    session = await record_device_session(test_session, device_data["group"].id, data)
    assert session.device_type == "android"
    assert session.ended_at is not None


@pytest.mark.asyncio
async def test_record_device_session_tablet(test_session: AsyncSession, device_data):
    """Record a tablet device session."""
    data = DeviceSessionCreate(
        member_id=device_data["member"].id,
        device_id="ipad-001",
        device_type="tablet",
        started_at=datetime(2026, 3, 21, 9, 0, 0, tzinfo=timezone.utc),
    )
    session = await record_device_session(test_session, device_data["group"].id, data)
    assert session.device_type == "tablet"
    assert session.os_version is None


@pytest.mark.asyncio
async def test_record_device_session_no_battery(test_session: AsyncSession, device_data):
    """Record a session without battery level."""
    data = DeviceSessionCreate(
        member_id=device_data["member"].id,
        device_id="device-no-bat",
        device_type="ios",
        started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
    )
    session = await record_device_session(test_session, device_data["group"].id, data)
    assert session.battery_level is None


@pytest.mark.asyncio
async def test_record_device_session_group_id_set(test_session: AsyncSession, device_data):
    """Group ID is stored on the device session."""
    data = DeviceSessionCreate(
        member_id=device_data["member"].id,
        device_id="device-grp",
        device_type="ios",
        started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
    )
    session = await record_device_session(test_session, device_data["group"].id, data)
    assert session.group_id == device_data["group"].id


# ---------------------------------------------------------------------------
# App Usage Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_app_usage_session(test_session: AsyncSession, device_data):
    """Record app usage with app_name, bundle_id, foreground_minutes."""
    data = AppUsageCreate(
        member_id=device_data["member"].id,
        app_name="TikTok",
        bundle_id="com.zhiliaoapp.musically",
        category="social",
        started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 21, 10, 30, 0, tzinfo=timezone.utc),
        foreground_minutes=30.0,
    )
    record = await record_app_usage(test_session, device_data["group"].id, data)
    assert record.id is not None
    assert record.app_name == "TikTok"
    assert record.bundle_id == "com.zhiliaoapp.musically"
    assert record.foreground_minutes == 30.0
    assert record.category == "social"


@pytest.mark.asyncio
async def test_record_app_usage_education(test_session: AsyncSession, device_data):
    """Record education app usage."""
    data = AppUsageCreate(
        member_id=device_data["member"].id,
        app_name="Khan Academy",
        bundle_id="org.khanacademy.khan",
        category="education",
        started_at=datetime(2026, 3, 21, 14, 0, 0, tzinfo=timezone.utc),
        foreground_minutes=45.0,
    )
    record = await record_app_usage(test_session, device_data["group"].id, data)
    assert record.category == "education"
    assert record.foreground_minutes == 45.0


@pytest.mark.asyncio
async def test_record_app_usage_games(test_session: AsyncSession, device_data):
    """Record games app usage."""
    data = AppUsageCreate(
        member_id=device_data["member"].id,
        app_name="Minecraft",
        bundle_id="com.mojang.minecraftpe",
        category="games",
        started_at=datetime(2026, 3, 21, 16, 0, 0, tzinfo=timezone.utc),
        foreground_minutes=60.0,
    )
    record = await record_app_usage(test_session, device_data["group"].id, data)
    assert record.category == "games"


@pytest.mark.asyncio
async def test_record_app_usage_zero_minutes(test_session: AsyncSession, device_data):
    """Record app usage with zero foreground minutes."""
    data = AppUsageCreate(
        member_id=device_data["member"].id,
        app_name="Camera",
        bundle_id="com.apple.camera",
        category="other",
        started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
        foreground_minutes=0.0,
    )
    record = await record_app_usage(test_session, device_data["group"].id, data)
    assert record.foreground_minutes == 0.0


@pytest.mark.asyncio
async def test_record_app_usage_with_session_id(test_session: AsyncSession, device_data):
    """Record app usage linked to a device session."""
    session_data = DeviceSessionCreate(
        member_id=device_data["member"].id,
        device_id="device-linked",
        device_type="ios",
        started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
    )
    session = await record_device_session(test_session, device_data["group"].id, session_data)

    usage_data = AppUsageCreate(
        member_id=device_data["member"].id,
        session_id=session.id,
        app_name="Safari",
        bundle_id="com.apple.safari",
        category="productivity",
        started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
        foreground_minutes=15.0,
    )
    record = await record_app_usage(test_session, device_data["group"].id, usage_data)
    assert record.session_id == session.id


@pytest.mark.asyncio
async def test_record_app_usage_default_category(test_session: AsyncSession, device_data):
    """Default category is 'other'."""
    data = AppUsageCreate(
        member_id=device_data["member"].id,
        app_name="Mystery App",
        bundle_id="com.mystery.app",
        started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
        foreground_minutes=5.0,
    )
    record = await record_app_usage(test_session, device_data["group"].id, data)
    assert record.category == "other"


# ---------------------------------------------------------------------------
# App Usage History Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_app_usage_history_empty(test_session: AsyncSession, device_data):
    """Empty usage history returns empty list."""
    items, total = await get_app_usage_history(
        test_session, device_data["group"].id, device_data["member"].id,
    )
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_app_usage_history_with_records(test_session: AsyncSession, device_data):
    """Usage history returns recorded items."""
    for i in range(3):
        data = AppUsageCreate(
            member_id=device_data["member"].id,
            app_name=f"App {i}",
            bundle_id=f"com.test.app{i}",
            started_at=datetime(2026, 3, 21, 10 + i, 0, 0, tzinfo=timezone.utc),
            foreground_minutes=10.0 * (i + 1),
        )
        await record_app_usage(test_session, device_data["group"].id, data)

    items, total = await get_app_usage_history(
        test_session, device_data["group"].id, device_data["member"].id,
    )
    assert total == 3
    assert len(items) == 3


@pytest.mark.asyncio
async def test_get_app_usage_history_pagination(test_session: AsyncSession, device_data):
    """Usage history supports pagination."""
    for i in range(5):
        data = AppUsageCreate(
            member_id=device_data["member"].id,
            app_name=f"App {i}",
            bundle_id=f"com.test.app{i}",
            started_at=datetime(2026, 3, 21, 10 + i, 0, 0, tzinfo=timezone.utc),
            foreground_minutes=5.0,
        )
        await record_app_usage(test_session, device_data["group"].id, data)

    items, total = await get_app_usage_history(
        test_session, device_data["group"].id, device_data["member"].id,
        offset=0, limit=2,
    )
    assert total == 5
    assert len(items) == 2


@pytest.mark.asyncio
async def test_get_app_usage_history_filter_category(test_session: AsyncSession, device_data):
    """Usage history can be filtered by category."""
    for cat in ["social", "education", "social"]:
        data = AppUsageCreate(
            member_id=device_data["member"].id,
            app_name=f"App-{cat}",
            bundle_id=f"com.test.{cat}",
            category=cat,
            started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
            foreground_minutes=10.0,
        )
        await record_app_usage(test_session, device_data["group"].id, data)

    items, total = await get_app_usage_history(
        test_session, device_data["group"].id, device_data["member"].id,
        category="social",
    )
    assert total == 2


# ---------------------------------------------------------------------------
# Screen Time Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_screen_time_summary(test_session: AsyncSession, device_data):
    """Get total_minutes, app_breakdown, category_breakdown for a date."""
    # Create usage records
    for app, cat, mins in [("TikTok", "social", 30), ("YouTube", "entertainment", 45), ("Duolingo", "education", 20)]:
        data = AppUsageCreate(
            member_id=device_data["member"].id,
            app_name=app,
            bundle_id=f"com.test.{app.lower()}",
            category=cat,
            started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
            foreground_minutes=float(mins),
        )
        await record_app_usage(test_session, device_data["group"].id, data)

    # Update screen time for the date
    screen_time = await update_screen_time(
        test_session, device_data["group"].id, device_data["member"].id,
        date(2026, 3, 21),
    )

    assert screen_time.total_minutes == 95.0
    assert screen_time.app_breakdown["TikTok"] == 30.0
    assert screen_time.app_breakdown["YouTube"] == 45.0
    assert screen_time.category_breakdown["social"] == 30.0
    assert screen_time.category_breakdown["entertainment"] == 45.0
    assert screen_time.category_breakdown["education"] == 20.0


@pytest.mark.asyncio
async def test_get_screen_time_summary_not_found(test_session: AsyncSession, device_data):
    """Screen time for a date with no data raises NotFoundError."""
    with pytest.raises(NotFoundError):
        await get_screen_time_summary(
            test_session, device_data["group"].id, device_data["member"].id,
            date(2026, 1, 1),
        )


@pytest.mark.asyncio
async def test_update_screen_time_creates_record(test_session: AsyncSession, device_data):
    """update_screen_time creates a record if none exists."""
    screen_time = await update_screen_time(
        test_session, device_data["group"].id, device_data["member"].id,
        date(2026, 3, 20),
    )
    assert screen_time.total_minutes == 0.0
    assert screen_time.pickups == 0


@pytest.mark.asyncio
async def test_update_screen_time_upserts(test_session: AsyncSession, device_data):
    """update_screen_time updates existing record."""
    # Create initial
    await update_screen_time(
        test_session, device_data["group"].id, device_data["member"].id,
        date(2026, 3, 19),
    )

    # Add usage
    data = AppUsageCreate(
        member_id=device_data["member"].id,
        app_name="App",
        bundle_id="com.test.app",
        started_at=datetime(2026, 3, 19, 10, 0, 0, tzinfo=timezone.utc),
        foreground_minutes=25.0,
    )
    await record_app_usage(test_session, device_data["group"].id, data)

    # Update again
    screen_time = await update_screen_time(
        test_session, device_data["group"].id, device_data["member"].id,
        date(2026, 3, 19),
    )
    assert screen_time.total_minutes == 25.0


@pytest.mark.asyncio
async def test_screen_time_date_stored(test_session: AsyncSession, device_data):
    """Screen time record stores the correct date."""
    target = date(2026, 3, 15)
    screen_time = await update_screen_time(
        test_session, device_data["group"].id, device_data["member"].id,
        target,
    )
    assert screen_time.date == target


# ---------------------------------------------------------------------------
# Batch Sync Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_device_data_basic(test_session: AsyncSession, device_data):
    """Basic batch sync creates sessions and usage records."""
    sync_req = DeviceSyncRequest(
        member_id=device_data["member"].id,
        device_id="sync-device",
        device_type="ios",
        sessions=[
            DeviceSessionCreate(
                member_id=device_data["member"].id,
                device_id="sync-device",
                device_type="ios",
                started_at=datetime(2026, 3, 21, 8, 0, 0, tzinfo=timezone.utc),
            ),
        ],
        usage_records=[
            AppUsageCreate(
                member_id=device_data["member"].id,
                app_name="ChatGPT",
                bundle_id="com.openai.chatgpt",
                category="productivity",
                started_at=datetime(2026, 3, 21, 8, 5, 0, tzinfo=timezone.utc),
                foreground_minutes=20.0,
            ),
        ],
    )
    result = await sync_device_data(test_session, device_data["group"].id, sync_req)
    assert result["sessions_created"] == 1
    assert result["usage_records_created"] == 1
    assert result["screen_time_updated"] is True


@pytest.mark.asyncio
async def test_sync_device_data_empty(test_session: AsyncSession, device_data):
    """Sync with no data creates nothing."""
    sync_req = DeviceSyncRequest(
        member_id=device_data["member"].id,
        device_id="sync-empty",
        device_type="android",
    )
    result = await sync_device_data(test_session, device_data["group"].id, sync_req)
    assert result["sessions_created"] == 0
    assert result["usage_records_created"] == 0
    assert result["screen_time_updated"] is False


@pytest.mark.asyncio
async def test_sync_device_data_multiple_usage(test_session: AsyncSession, device_data):
    """Sync with multiple usage records."""
    sync_req = DeviceSyncRequest(
        member_id=device_data["member"].id,
        device_id="sync-multi",
        device_type="ios",
        usage_records=[
            AppUsageCreate(
                member_id=device_data["member"].id,
                app_name=f"App {i}",
                bundle_id=f"com.test.app{i}",
                started_at=datetime(2026, 3, 21, 10 + i, 0, 0, tzinfo=timezone.utc),
                foreground_minutes=10.0,
            )
            for i in range(3)
        ],
    )
    result = await sync_device_data(test_session, device_data["group"].id, sync_req)
    assert result["usage_records_created"] == 3
    assert result["screen_time_updated"] is True


@pytest.mark.asyncio
async def test_sync_updates_screen_time(test_session: AsyncSession, device_data):
    """Sync recalculates screen time after adding usage."""
    sync_req = DeviceSyncRequest(
        member_id=device_data["member"].id,
        device_id="sync-screen",
        device_type="ios",
        usage_records=[
            AppUsageCreate(
                member_id=device_data["member"].id,
                app_name="App A",
                bundle_id="com.test.a",
                category="social",
                started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
                foreground_minutes=15.0,
            ),
            AppUsageCreate(
                member_id=device_data["member"].id,
                app_name="App B",
                bundle_id="com.test.b",
                category="education",
                started_at=datetime(2026, 3, 21, 11, 0, 0, tzinfo=timezone.utc),
                foreground_minutes=25.0,
            ),
        ],
    )
    await sync_device_data(test_session, device_data["group"].id, sync_req)

    screen_time = await get_screen_time_summary(
        test_session, device_data["group"].id, device_data["member"].id,
        date(2026, 3, 21),
    )
    assert screen_time.total_minutes == 40.0


# ---------------------------------------------------------------------------
# Additional Unit Tests — Schema Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_device_session_schema_valid():
    """DeviceSessionCreate validates valid data."""
    data = DeviceSessionCreate(
        member_id=uuid.uuid4(),
        device_id="valid-device",
        device_type="ios",
        started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
    )
    assert data.device_type == "ios"


@pytest.mark.asyncio
async def test_device_session_schema_rejects_bad_type():
    """DeviceSessionCreate rejects invalid device_type."""
    from pydantic import ValidationError as PydanticError
    with pytest.raises(PydanticError):
        DeviceSessionCreate(
            member_id=uuid.uuid4(),
            device_id="bad",
            device_type="smartfridge",
            started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
        )


@pytest.mark.asyncio
async def test_app_usage_schema_rejects_negative_minutes():
    """AppUsageCreate rejects negative foreground_minutes."""
    from pydantic import ValidationError as PydanticError
    with pytest.raises(PydanticError):
        AppUsageCreate(
            member_id=uuid.uuid4(),
            app_name="App",
            bundle_id="com.test.app",
            started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
            foreground_minutes=-10.0,
        )


@pytest.mark.asyncio
async def test_app_usage_schema_rejects_invalid_category():
    """AppUsageCreate rejects invalid category."""
    from pydantic import ValidationError as PydanticError
    with pytest.raises(PydanticError):
        AppUsageCreate(
            member_id=uuid.uuid4(),
            app_name="App",
            bundle_id="com.test.app",
            category="invalid",
            started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
            foreground_minutes=5.0,
        )


@pytest.mark.asyncio
async def test_battery_level_valid_range():
    """DeviceSessionCreate accepts battery_level 0-100."""
    data = DeviceSessionCreate(
        member_id=uuid.uuid4(),
        device_id="bat-test",
        device_type="android",
        started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
        battery_level=0.0,
    )
    assert data.battery_level == 0.0

    data2 = DeviceSessionCreate(
        member_id=uuid.uuid4(),
        device_id="bat-test2",
        device_type="android",
        started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
        battery_level=100.0,
    )
    assert data2.battery_level == 100.0


@pytest.mark.asyncio
async def test_battery_level_rejects_over_100():
    """DeviceSessionCreate rejects battery_level > 100."""
    from pydantic import ValidationError as PydanticError
    with pytest.raises(PydanticError):
        DeviceSessionCreate(
            member_id=uuid.uuid4(),
            device_id="bad-bat",
            device_type="ios",
            started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
            battery_level=150.0,
        )


@pytest.mark.asyncio
async def test_get_app_usage_history_date_filter(test_session: AsyncSession, device_data):
    """Usage history can be filtered by date range."""
    # Usage on different dates
    for day in [18, 19, 20]:
        data = AppUsageCreate(
            member_id=device_data["member"].id,
            app_name=f"App-{day}",
            bundle_id=f"com.test.app{day}",
            started_at=datetime(2026, 3, day, 10, 0, 0, tzinfo=timezone.utc),
            foreground_minutes=10.0,
        )
        await record_app_usage(test_session, device_data["group"].id, data)

    items, total = await get_app_usage_history(
        test_session, device_data["group"].id, device_data["member"].id,
        start_date=date(2026, 3, 19),
        end_date=date(2026, 3, 20),
    )
    assert total == 2


@pytest.mark.asyncio
async def test_screen_time_range_multiple_days(test_session: AsyncSession, device_data):
    """Screen time range returns records for multiple days."""
    from src.device_agent.service import get_screen_time_range

    for day in [14, 15, 16]:
        data = AppUsageCreate(
            member_id=device_data["member"].id,
            app_name=f"App-{day}",
            bundle_id=f"com.test.app{day}",
            started_at=datetime(2026, 3, day, 10, 0, 0, tzinfo=timezone.utc),
            foreground_minutes=10.0 * day,
        )
        await record_app_usage(test_session, device_data["group"].id, data)
        await update_screen_time(
            test_session, device_data["group"].id, device_data["member"].id,
            date(2026, 3, day),
        )

    items = await get_screen_time_range(
        test_session, device_data["group"].id, device_data["member"].id,
        date(2026, 3, 14), date(2026, 3, 16),
    )
    assert len(items) == 3
    # Verify ordering
    assert items[0].date < items[1].date < items[2].date


@pytest.mark.asyncio
async def test_screen_time_range_empty(test_session: AsyncSession, device_data):
    """Screen time range returns empty for dates with no data."""
    from src.device_agent.service import get_screen_time_range

    items = await get_screen_time_range(
        test_session, device_data["group"].id, device_data["member"].id,
        date(2025, 1, 1), date(2025, 1, 7),
    )
    assert items == []
