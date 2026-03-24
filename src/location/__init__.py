"""Location module — tracking, geofencing, school check-in, privacy controls.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

from src.location.service import (
    activate_kill_switch,
    check_geofence,
    create_geofence,
    create_school_consent,
    deactivate_kill_switch,
    delete_geofence,
    delete_location_history,
    get_audit_log,
    get_current_location,
    get_kill_switch_status,
    get_location_history,
    get_school_attendance,
    haversine_distance,
    list_geofences,
    purge_expired_locations,
    record_check_in,
    record_check_out,
    report_location,
    revoke_school_consent,
)

__all__ = [
    "activate_kill_switch",
    "check_geofence",
    "create_geofence",
    "create_school_consent",
    "deactivate_kill_switch",
    "delete_geofence",
    "delete_location_history",
    "get_audit_log",
    "get_current_location",
    "get_kill_switch_status",
    "get_location_history",
    "get_school_attendance",
    "haversine_distance",
    "list_geofences",
    "purge_expired_locations",
    "record_check_in",
    "record_check_out",
    "report_location",
    "revoke_school_consent",
]
