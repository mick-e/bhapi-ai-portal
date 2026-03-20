"""Unit tests for Google Admin Console integration."""

import pytest
from datetime import datetime, timezone

from src.integrations.google_admin import (
    GoogleAdminIntegration,
    DeviceStatus,
    DeploymentStatus,
    VALID_DEVICE_STATUSES,
)


@pytest.fixture
def admin():
    """Create a fresh GoogleAdminIntegration instance."""
    return GoogleAdminIntegration()


@pytest.fixture
async def admin_with_school(admin):
    """Admin integration with one school already registered."""
    await admin.register_school("school-1", "Test School", "admin@school.com")
    return admin


# ─── Registration ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_school(admin):
    """Registering a school returns the correct status."""
    result = await admin.register_school("s1", "Lincoln High", "admin@lincoln.com")
    assert result["school_id"] == "s1"
    assert result["status"] == "registered"


@pytest.mark.asyncio
async def test_register_school_duplicate(admin):
    """Registering the same school twice raises ValueError."""
    await admin.register_school("s1", "School", "admin@school.com")
    with pytest.raises(ValueError, match="already registered"):
        await admin.register_school("s1", "School", "admin@school.com")


@pytest.mark.asyncio
async def test_register_school_empty_id(admin):
    """Empty school_id raises ValueError."""
    with pytest.raises(ValueError, match="school_id"):
        await admin.register_school("", "School", "admin@school.com")


@pytest.mark.asyncio
async def test_register_school_empty_name(admin):
    """Empty school_name raises ValueError."""
    with pytest.raises(ValueError, match="school_name"):
        await admin.register_school("s1", "", "admin@school.com")


@pytest.mark.asyncio
async def test_register_school_invalid_email(admin):
    """Invalid email raises ValueError."""
    with pytest.raises(ValueError, match="email"):
        await admin.register_school("s1", "School", "not-an-email")


@pytest.mark.asyncio
async def test_unregister_school(admin_with_school):
    """Unregistering a school removes it."""
    result = await admin_with_school.unregister_school("school-1")
    assert result["status"] == "unregistered"
    assert await admin_with_school.get_school("school-1") is None


@pytest.mark.asyncio
async def test_unregister_school_not_found(admin):
    """Unregistering a missing school raises KeyError."""
    with pytest.raises(KeyError):
        await admin.unregister_school("nonexistent")


@pytest.mark.asyncio
async def test_get_school(admin_with_school):
    """Get school returns registration data."""
    school = await admin_with_school.get_school("school-1")
    assert school is not None
    assert school["school_name"] == "Test School"
    assert school["admin_email"] == "admin@school.com"


@pytest.mark.asyncio
async def test_get_school_not_found(admin):
    """Get school for missing ID returns None."""
    assert await admin.get_school("nope") is None


@pytest.mark.asyncio
async def test_list_schools(admin):
    """List schools returns all registered schools."""
    await admin.register_school("s1", "School A", "a@a.com")
    await admin.register_school("s2", "School B", "b@b.com")
    schools = await admin.list_schools()
    assert len(schools) == 2
    ids = {s["school_id"] for s in schools}
    assert ids == {"s1", "s2"}


# ─── Devices ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_device(admin_with_school):
    """Adding a device returns a pending DeviceStatus."""
    device = await admin_with_school.add_device("school-1", "dev-1", serial_number="SN001")
    assert isinstance(device, DeviceStatus)
    assert device.device_id == "dev-1"
    assert device.status == "pending"
    assert device.serial_number == "SN001"


@pytest.mark.asyncio
async def test_add_device_school_not_found(admin):
    """Adding a device for unregistered school raises KeyError."""
    with pytest.raises(KeyError):
        await admin.add_device("missing", "dev-1")


@pytest.mark.asyncio
async def test_add_device_empty_id(admin_with_school):
    """Adding a device with empty ID raises ValueError."""
    with pytest.raises(ValueError, match="device_id"):
        await admin_with_school.add_device("school-1", "")


@pytest.mark.asyncio
async def test_add_device_duplicate(admin_with_school):
    """Adding the same device twice raises ValueError."""
    await admin_with_school.add_device("school-1", "dev-1")
    with pytest.raises(ValueError, match="already exists"):
        await admin_with_school.add_device("school-1", "dev-1")


@pytest.mark.asyncio
async def test_remove_device(admin_with_school):
    """Removing a device returns True."""
    await admin_with_school.add_device("school-1", "dev-1")
    assert await admin_with_school.remove_device("school-1", "dev-1") is True


@pytest.mark.asyncio
async def test_remove_device_not_found(admin_with_school):
    """Removing a non-existent device returns False."""
    assert await admin_with_school.remove_device("school-1", "nope") is False


@pytest.mark.asyncio
async def test_update_device_status_deployed(admin_with_school):
    """Updating device status to deployed works."""
    await admin_with_school.add_device("school-1", "dev-1")
    device = await admin_with_school.update_device_status("school-1", "dev-1", "deployed")
    assert device is not None
    assert device.status == "deployed"
    assert device.last_sync is not None


@pytest.mark.asyncio
async def test_update_device_status_invalid(admin_with_school):
    """Invalid status raises ValueError."""
    await admin_with_school.add_device("school-1", "dev-1")
    with pytest.raises(ValueError, match="Invalid status"):
        await admin_with_school.update_device_status("school-1", "dev-1", "bogus")


@pytest.mark.asyncio
async def test_update_device_status_not_found(admin_with_school):
    """Updating a non-existent device returns None."""
    result = await admin_with_school.update_device_status("school-1", "missing", "deployed")
    assert result is None


@pytest.mark.asyncio
async def test_list_devices_all(admin_with_school):
    """List devices returns all devices for a school."""
    await admin_with_school.add_device("school-1", "dev-1")
    await admin_with_school.add_device("school-1", "dev-2")
    devices = await admin_with_school.list_devices("school-1")
    assert len(devices) == 2


@pytest.mark.asyncio
async def test_list_devices_filtered(admin_with_school):
    """List devices filtered by status returns subset."""
    await admin_with_school.add_device("school-1", "dev-1")
    await admin_with_school.add_device("school-1", "dev-2")
    await admin_with_school.update_device_status("school-1", "dev-1", "deployed")
    devices = await admin_with_school.list_devices("school-1", status="deployed")
    assert len(devices) == 1
    assert devices[0].device_id == "dev-1"


@pytest.mark.asyncio
async def test_list_devices_invalid_filter(admin_with_school):
    """Invalid status filter raises ValueError."""
    with pytest.raises(ValueError, match="Invalid status filter"):
        await admin_with_school.list_devices("school-1", status="bogus")


@pytest.mark.asyncio
async def test_list_devices_school_not_found(admin):
    """List devices for unregistered school raises KeyError."""
    with pytest.raises(KeyError):
        await admin.list_devices("missing")


# ─── Deployment Status ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deployment_status_empty(admin_with_school):
    """Deployment status with no devices shows zeros."""
    status = await admin_with_school.get_deployment_status("school-1")
    assert status is not None
    assert status.total_devices == 0
    assert status.deployment_percentage == 0.0


@pytest.mark.asyncio
async def test_deployment_status_partial(admin_with_school):
    """Deployment percentage reflects actual deployment."""
    await admin_with_school.add_device("school-1", "d1")
    await admin_with_school.add_device("school-1", "d2")
    await admin_with_school.add_device("school-1", "d3")
    await admin_with_school.add_device("school-1", "d4")
    await admin_with_school.update_device_status("school-1", "d1", "deployed")
    await admin_with_school.update_device_status("school-1", "d2", "deployed")
    await admin_with_school.update_device_status("school-1", "d3", "error")
    status = await admin_with_school.get_deployment_status("school-1")
    assert status.total_devices == 4
    assert status.deployed == 2
    assert status.pending == 1
    assert status.errors == 1
    assert status.deployment_percentage == 50.0


@pytest.mark.asyncio
async def test_deployment_status_not_found(admin):
    """Deployment status for unregistered school returns None."""
    assert await admin.get_deployment_status("missing") is None


# ─── Policy ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_push_policy(admin_with_school):
    """Pushing a policy stores and returns it."""
    policy = {"content_filtering": True, "safe_search": True}
    result = await admin_with_school.push_policy("school-1", policy)
    assert result["status"] == "policy_pushed"
    assert result["policy"] == policy


@pytest.mark.asyncio
async def test_push_policy_school_not_found(admin):
    """Pushing policy for unregistered school raises KeyError."""
    with pytest.raises(KeyError):
        await admin.push_policy("missing", {"k": "v"})


@pytest.mark.asyncio
async def test_push_policy_empty(admin_with_school):
    """Pushing empty policy raises ValueError."""
    with pytest.raises(ValueError, match="must not be empty"):
        await admin_with_school.push_policy("school-1", {})


@pytest.mark.asyncio
async def test_get_active_policy(admin_with_school):
    """Get active policy returns the last pushed policy."""
    policy = {"monitoring_level": "strict"}
    await admin_with_school.push_policy("school-1", policy)
    result = await admin_with_school.get_active_policy("school-1")
    assert result == policy


@pytest.mark.asyncio
async def test_get_active_policy_none(admin_with_school):
    """Get active policy when none pushed returns None."""
    result = await admin_with_school.get_active_policy("school-1")
    assert result is None


# ─── Force Install ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_force_install_extension(admin_with_school):
    """Force install configures the extension."""
    result = await admin_with_school.force_install_extension("school-1", "ext-abc123")
    assert result["status"] == "force_install_configured"
    assert result["extension_id"] == "ext-abc123"


@pytest.mark.asyncio
async def test_force_install_school_not_found(admin):
    """Force install for unregistered school raises KeyError."""
    with pytest.raises(KeyError):
        await admin.force_install_extension("missing", "ext-1")


@pytest.mark.asyncio
async def test_force_install_empty_extension_id(admin_with_school):
    """Force install with empty extension_id raises ValueError."""
    with pytest.raises(ValueError, match="extension_id"):
        await admin_with_school.force_install_extension("school-1", "")


@pytest.mark.asyncio
async def test_get_force_install_status(admin_with_school):
    """Get force install status after configuration."""
    await admin_with_school.force_install_extension("school-1", "ext-123")
    result = await admin_with_school.get_force_install_status("school-1")
    assert result is not None
    assert result["extension_id"] == "ext-123"


# ─── Bulk & Misc ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bulk_add_devices(admin_with_school):
    """Bulk add creates all devices."""
    devices = [
        {"device_id": "d1", "serial_number": "SN1"},
        {"device_id": "d2", "os_version": "ChromeOS 120"},
        {"device_id": "d3"},
    ]
    results = await admin_with_school.bulk_add_devices("school-1", devices)
    assert len(results) == 3
    assert all(d.status == "pending" for d in results)


@pytest.mark.asyncio
async def test_bulk_add_devices_school_not_found(admin):
    """Bulk add for unregistered school raises KeyError."""
    with pytest.raises(KeyError):
        await admin.bulk_add_devices("missing", [{"device_id": "d1"}])


@pytest.mark.asyncio
async def test_configure_sets_credentials(admin):
    """Configure stores API key and customer ID."""
    admin.configure(api_key="key-123", customer_id="C001")
    assert admin.is_configured() is True


@pytest.mark.asyncio
async def test_not_configured_by_default(admin):
    """Integration is not configured by default."""
    assert admin.is_configured() is False


@pytest.mark.asyncio
async def test_reset_clears_state(admin_with_school):
    """Reset clears all deployments and devices."""
    await admin_with_school.add_device("school-1", "d1")
    admin_with_school.configure(api_key="k", customer_id="c")
    admin_with_school.reset()
    assert await admin_with_school.get_school("school-1") is None
    assert admin_with_school.is_configured() is False


@pytest.mark.asyncio
async def test_device_os_version_stored(admin_with_school):
    """OS version is stored on the device."""
    device = await admin_with_school.add_device("school-1", "d1", os_version="ChromeOS 121")
    assert device.os_version == "ChromeOS 121"


@pytest.mark.asyncio
async def test_whitespace_school_id_rejected(admin):
    """Whitespace-only school_id is rejected."""
    with pytest.raises(ValueError):
        await admin.register_school("   ", "School", "a@b.com")
