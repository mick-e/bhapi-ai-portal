"""Google Admin Console integration for school extension deployment."""

import structlog
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


logger = structlog.get_logger()


VALID_DEVICE_STATUSES = {"deployed", "pending", "error", "unknown"}
VALID_POLICY_FIELDS = {"content_filtering", "safe_search", "monitoring_level", "blocked_categories", "allowed_domains"}


@dataclass
class DeviceStatus:
    """Status of a managed Chromebook device."""

    device_id: str
    status: str  # deployed/pending/error/unknown
    last_sync: Optional[datetime] = None
    os_version: Optional[str] = None
    serial_number: Optional[str] = None


@dataclass
class DeploymentStatus:
    """Aggregate deployment status for a school."""

    school_id: str
    total_devices: int
    deployed: int
    pending: int
    errors: int
    deployment_percentage: float


@dataclass
class SchoolRegistration:
    """Registration record for a school."""

    school_id: str
    school_name: str
    admin_email: str
    registered_at: str
    status: str
    last_policy_push: Optional[str] = None
    active_policy: Optional[dict] = None
    force_install: Optional[dict] = None


class GoogleAdminIntegration:
    """Manages extension deployment via Google Admin Console."""

    def __init__(self) -> None:
        self._api_key: Optional[str] = None
        self._customer_id: Optional[str] = None
        # In-memory tracking (production would use DB)
        self._deployments: dict[str, dict] = {}  # school_id -> deployment data
        self._devices: dict[str, list[DeviceStatus]] = {}  # school_id -> devices

    def configure(
        self,
        api_key: Optional[str] = None,
        customer_id: Optional[str] = None,
    ) -> None:
        """Configure Google Admin API credentials."""
        self._api_key = api_key
        self._customer_id = customer_id

    def is_configured(self) -> bool:
        """Check whether API credentials are set."""
        return self._api_key is not None and self._customer_id is not None

    async def register_school(
        self,
        school_id: str,
        school_name: str,
        admin_email: str,
    ) -> dict:
        """Register a school for extension deployment."""
        if not school_id or not school_id.strip():
            raise ValueError("school_id must not be empty")
        if not school_name or not school_name.strip():
            raise ValueError("school_name must not be empty")
        if not admin_email or "@" not in admin_email:
            raise ValueError("admin_email must be a valid email address")

        if school_id in self._deployments:
            raise ValueError(f"School {school_id} is already registered")

        self._deployments[school_id] = {
            "school_name": school_name,
            "admin_email": admin_email,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "status": "registered",
        }
        self._devices[school_id] = []
        logger.info("school_registered", school_id=school_id, name=school_name)
        return {"school_id": school_id, "status": "registered"}

    async def unregister_school(self, school_id: str) -> dict:
        """Unregister a school and remove all device tracking."""
        if school_id not in self._deployments:
            raise KeyError(f"School {school_id} not found")

        del self._deployments[school_id]
        self._devices.pop(school_id, None)
        logger.info("school_unregistered", school_id=school_id)
        return {"school_id": school_id, "status": "unregistered"}

    async def get_school(self, school_id: str) -> dict | None:
        """Get school registration details."""
        return self._deployments.get(school_id)

    async def list_schools(self) -> list[dict]:
        """List all registered schools."""
        return [
            {"school_id": sid, **data}
            for sid, data in self._deployments.items()
        ]

    async def add_device(
        self,
        school_id: str,
        device_id: str,
        serial_number: Optional[str] = None,
        os_version: Optional[str] = None,
    ) -> DeviceStatus:
        """Add a device to tracking for a school."""
        if school_id not in self._deployments:
            raise KeyError(f"School {school_id} not found")
        if not device_id or not device_id.strip():
            raise ValueError("device_id must not be empty")

        # Check for duplicate device
        for dev in self._devices.get(school_id, []):
            if dev.device_id == device_id:
                raise ValueError(f"Device {device_id} already exists in school {school_id}")

        device = DeviceStatus(
            device_id=device_id,
            status="pending",
            last_sync=None,
            os_version=os_version,
            serial_number=serial_number,
        )
        self._devices[school_id].append(device)
        logger.info("device_added", school_id=school_id, device_id=device_id)
        return device

    async def remove_device(self, school_id: str, device_id: str) -> bool:
        """Remove a device from tracking."""
        devices = self._devices.get(school_id, [])
        for i, dev in enumerate(devices):
            if dev.device_id == device_id:
                devices.pop(i)
                logger.info("device_removed", school_id=school_id, device_id=device_id)
                return True
        return False

    async def update_device_status(
        self,
        school_id: str,
        device_id: str,
        status: str,
    ) -> DeviceStatus | None:
        """Update deployment status for a device."""
        if status not in VALID_DEVICE_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_DEVICE_STATUSES}")

        devices = self._devices.get(school_id, [])
        for dev in devices:
            if dev.device_id == device_id:
                dev.status = status
                dev.last_sync = datetime.now(timezone.utc)
                logger.info("device_status_updated", school_id=school_id, device_id=device_id, status=status)
                return dev
        return None

    async def get_deployment_status(self, school_id: str) -> DeploymentStatus | None:
        """Get overall deployment status for a school."""
        if school_id not in self._deployments:
            return None

        devices = self._devices.get(school_id, [])
        total = len(devices)
        deployed = sum(1 for d in devices if d.status == "deployed")
        pending = sum(1 for d in devices if d.status == "pending")
        errors = sum(1 for d in devices if d.status == "error")

        return DeploymentStatus(
            school_id=school_id,
            total_devices=total,
            deployed=deployed,
            pending=pending,
            errors=errors,
            deployment_percentage=(deployed / total * 100) if total > 0 else 0.0,
        )

    async def list_devices(
        self,
        school_id: str,
        status: Optional[str] = None,
    ) -> list[DeviceStatus]:
        """List devices for a school, optionally filtered by status."""
        if school_id not in self._deployments:
            raise KeyError(f"School {school_id} not found")

        devices = self._devices.get(school_id, [])
        if status:
            if status not in VALID_DEVICE_STATUSES:
                raise ValueError(f"Invalid status filter: {status}")
            return [d for d in devices if d.status == status]
        return list(devices)

    async def push_policy(self, school_id: str, policy: dict) -> dict:
        """Push a policy configuration to managed Chrome browsers."""
        if school_id not in self._deployments:
            raise KeyError(f"School {school_id} not found")
        if not policy:
            raise ValueError("Policy must not be empty")

        self._deployments[school_id]["last_policy_push"] = datetime.now(timezone.utc).isoformat()
        self._deployments[school_id]["active_policy"] = policy
        logger.info("policy_pushed", school_id=school_id)
        return {"school_id": school_id, "status": "policy_pushed", "policy": policy}

    async def get_active_policy(self, school_id: str) -> dict | None:
        """Get the active policy for a school."""
        if school_id not in self._deployments:
            return None
        return self._deployments[school_id].get("active_policy")

    async def force_install_extension(
        self,
        school_id: str,
        extension_id: str,
    ) -> dict:
        """Configure force-install of the extension via admin console."""
        if school_id not in self._deployments:
            raise KeyError(f"School {school_id} not found")
        if not extension_id or not extension_id.strip():
            raise ValueError("extension_id must not be empty")

        self._deployments[school_id]["force_install"] = {
            "extension_id": extension_id,
            "configured_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("force_install_configured", school_id=school_id, ext=extension_id)
        return {"school_id": school_id, "status": "force_install_configured", "extension_id": extension_id}

    async def get_force_install_status(self, school_id: str) -> dict | None:
        """Get force-install configuration for a school."""
        if school_id not in self._deployments:
            return None
        return self._deployments[school_id].get("force_install")

    async def bulk_add_devices(
        self,
        school_id: str,
        devices: list[dict],
    ) -> list[DeviceStatus]:
        """Add multiple devices at once."""
        if school_id not in self._deployments:
            raise KeyError(f"School {school_id} not found")

        results = []
        for dev_data in devices:
            device = await self.add_device(
                school_id,
                dev_data["device_id"],
                serial_number=dev_data.get("serial_number"),
                os_version=dev_data.get("os_version"),
            )
            results.append(device)
        return results

    def reset(self) -> None:
        """Reset all state. Useful for testing."""
        self._deployments.clear()
        self._devices.clear()
        self._api_key = None
        self._customer_id = None


# Module-level singleton
integration = GoogleAdminIntegration()
