"""Location module — tracking, geofencing, school check-in, privacy controls.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

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

__all__ = [
    "activate_kill_switch",
    "check_geofence",
    "create_geofence",
    "deactivate_kill_switch",
    "delete_geofence",
    "delete_location_history",
    "get_audit_log",
    "get_current_location",
    "get_kill_switch_status",
    "get_location_history",
    "haversine_distance",
    "list_geofences",
    "purge_expired_locations",
    "report_location",
]
