"""Alert & notification service module."""

from src.alerts.service import (
    create_alert,
    create_device_alert,
    create_social_alert,
    get_unified_alerts,
)

__all__ = [
    "create_alert",
    "create_device_alert",
    "create_social_alert",
    "get_unified_alerts",
]
