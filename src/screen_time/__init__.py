"""Screen time management module — rules, schedules, extension requests.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

from src.screen_time.service import (
    create_extension_request,
    create_rule,
    create_schedule,
    delete_rule,
    evaluate_usage,
    get_extension_requests,
    get_rules,
    get_schedules,
    get_weekly_report,
    respond_to_extension,
    update_rule,
)

__all__ = [
    "create_extension_request",
    "create_rule",
    "create_schedule",
    "delete_rule",
    "evaluate_usage",
    "get_extension_requests",
    "get_rules",
    "get_schedules",
    "get_weekly_report",
    "respond_to_extension",
    "update_rule",
]
