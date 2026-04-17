"""Device agent — app usage, screen time, background sync.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

from src.device_agent.schemas import (
    PushTokenCreate,
    PushTokenListResponse,
    PushTokenResponse,
)
from src.device_agent.service import (
    get_app_usage_history,
    get_screen_time_range,
    get_screen_time_summary,
    record_app_usage,
    record_device_session,
    sync_device_data,
    update_screen_time,
)

# Public interface for cross-module access
from .models import AppUsageRecord, DeviceSession, ScreenTimeRecord

__all__ = [
    "PushTokenCreate",
    "PushTokenListResponse",
    "PushTokenResponse",
    "get_app_usage_history",
    "get_screen_time_range",
    "get_screen_time_summary",
    "record_app_usage",
    "record_device_session",
    "sync_device_data",
    "update_screen_time",
    "AppUsageRecord",
    "DeviceSession",
    "ScreenTimeRecord",
]
