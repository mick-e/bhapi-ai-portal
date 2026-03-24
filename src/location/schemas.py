"""Pydantic v2 schemas for the location module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Location Records
# ---------------------------------------------------------------------------


class LocationReportCreate(BaseModel):
    """Schema for reporting a location data point from the device agent."""

    member_id: UUID
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    accuracy: float = Field(..., ge=0.0)
    source: str = Field(default="gps", pattern=r"^(gps|network|fused)$")
    recorded_at: datetime


class LocationRecordResponse(BaseModel):
    """Schema for location record responses (coordinates are encrypted in storage)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    group_id: UUID
    accuracy: float
    source: str
    recorded_at: datetime
    created_at: datetime


# ---------------------------------------------------------------------------
# Geofences
# ---------------------------------------------------------------------------


class GeofenceCreate(BaseModel):
    """Schema for creating a geofence boundary."""

    member_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    radius_meters: float = Field(..., gt=0.0, le=50000.0)
    notify_on_enter: bool = True
    notify_on_exit: bool = True


class GeofenceResponse(BaseModel):
    """Schema for geofence responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    member_id: UUID
    name: str
    latitude: float
    longitude: float
    radius_meters: float
    notify_on_enter: bool
    notify_on_exit: bool
    created_at: datetime
    updated_at: datetime


class GeofenceListResponse(BaseModel):
    """Paginated list of geofences."""

    items: list[GeofenceResponse]
    total: int


# ---------------------------------------------------------------------------
# Geofence Events
# ---------------------------------------------------------------------------


class GeofenceEventResponse(BaseModel):
    """Schema for geofence event responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    geofence_id: UUID
    member_id: UUID
    event_type: str  # enter, exit
    recorded_at: datetime
    created_at: datetime


# ---------------------------------------------------------------------------
# School Check-In
# ---------------------------------------------------------------------------


class SchoolCheckInResponse(BaseModel):
    """Schema for school check-in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    group_id: UUID
    geofence_id: UUID
    check_in_at: datetime
    check_out_at: datetime | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Location Sharing Consent
# ---------------------------------------------------------------------------


class LocationConsentCreate(BaseModel):
    """Schema for granting location sharing consent to a school."""

    member_id: UUID
    school_group_id: UUID
    granted_at: datetime


class LocationConsentResponse(BaseModel):
    """Schema for location consent responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    group_id: UUID
    granted_by: UUID
    granted_at: datetime
    revoked_at: datetime | None = None
    created_at: datetime

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


# ---------------------------------------------------------------------------
# Kill Switch
# ---------------------------------------------------------------------------


class KillSwitchResponse(BaseModel):
    """Schema for kill switch responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    activated_by: UUID
    activated_at: datetime
    deactivated_at: datetime | None = None
    created_at: datetime

    @property
    def is_active(self) -> bool:
        return self.deactivated_at is None


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------


class AuditLogResponse(BaseModel):
    """Schema for a single location audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    accessor_id: UUID
    data_type: str  # current, history, checkin
    accessed_at: datetime
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """Paginated list of audit log entries."""

    items: list[AuditLogResponse]
    total: int
    offset: int
    limit: int
    has_more: bool


# ---------------------------------------------------------------------------
# School Check-In — request schemas
# ---------------------------------------------------------------------------


class SchoolConsentCreate(BaseModel):
    """Schema for granting school check-in consent (parent → school)."""

    member_id: UUID
    school_group_id: UUID


class CheckInCreate(BaseModel):
    """Schema for recording a school check-in."""

    member_id: UUID
    geofence_id: UUID


class CheckOutCreate(BaseModel):
    """Schema for recording a school check-out."""

    member_id: UUID
    geofence_id: UUID


# ---------------------------------------------------------------------------
# School attendance — response schemas (no coordinates)
# ---------------------------------------------------------------------------


class AttendanceRecord(BaseModel):
    """A single attendance entry — timestamps only, never coordinates."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    geofence_id: UUID
    check_in_at: datetime
    check_out_at: datetime | None = None


class AttendanceListResponse(BaseModel):
    """List of attendance records for a school on a given date."""

    items: list[AttendanceRecord]
    total: int
    date: datetime
