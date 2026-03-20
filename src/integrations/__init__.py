"""Public interface for integrations module."""

from src.integrations.google_admin import (
    GoogleAdminIntegration,
    DeviceStatus,
    DeploymentStatus,
    integration as google_admin_integration,
)

__all__ = [
    "GoogleAdminIntegration",
    "DeviceStatus",
    "DeploymentStatus",
    "google_admin_integration",
]
