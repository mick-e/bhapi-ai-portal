"""Alert & notification service module."""

from src.alerts.service import (
    create_alert,
    create_device_alert,
    create_social_alert,
    get_unified_alerts,
)

# Public interface for cross-module access
from .models import Alert, NotificationPreference
from .push import expo_push_service
from .schemas import AlertCreate

__all__ = [
    "create_alert",
    "create_device_alert",
    "create_social_alert",
    "get_unified_alerts",
    "Alert",
    "NotificationPreference",
    "expo_push_service",
    "AlertCreate",
]
