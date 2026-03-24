/**
 * Location types for the Bhapi Safety (parent) app.
 * API: /api/v1/location/
 */

export type GeofenceType = 'home' | 'school' | 'custom';

export interface LocationPoint {
  lat: number;
  lng: number;
  timestamp: string;
  accuracy: number | null; // meters, null if unknown
  source: 'gps' | 'network' | 'passive';
}

export interface Geofence {
  id: string;
  name: string;
  lat: number;
  lng: number;
  radius_meters: number;
  type: GeofenceType;
  alerts_enabled: boolean;
}

export interface LocationHistory {
  member_id: string;
  points: LocationPoint[];
  date: string; // ISO date string YYYY-MM-DD
}

export interface LocationSettings {
  tracking_enabled: boolean;
  history_retention_days: number; // 7, 14, 30, or 90
  geofences: Geofence[];
}
