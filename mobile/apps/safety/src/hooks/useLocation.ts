/**
 * Location React Query hooks for the Bhapi Safety (parent) app.
 * API: /api/v1/location/
 *
 * Provides hooks for location history, geofence CRUD, and location settings.
 * All data fetching uses @tanstack/react-query.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  LocationHistory,
  Geofence,
  LocationSettings,
  GeofenceType,
} from '@bhapi/types';
import { ApiClient } from '@bhapi/api';

const apiClient = new ApiClient({ baseUrl: '' });

// ---- Query keys ----

const KEYS = {
  history: (memberId: string, date?: string) =>
    ['location', 'history', memberId, date ?? 'today'] as const,
  geofences: (groupId: string) => ['location', 'geofences', groupId] as const,
  settings: (memberId: string) => ['location', 'settings', memberId] as const,
};

// ---- Location history ----

export function useLocationHistory(memberId: string, date?: string) {
  const params = new URLSearchParams({ member_id: memberId });
  if (date) params.set('date', date);
  return useQuery<LocationHistory>({
    queryKey: KEYS.history(memberId, date),
    queryFn: () =>
      apiClient.get<LocationHistory>(`/api/v1/location/history?${params}`),
    enabled: Boolean(memberId),
    staleTime: 30_000, // 30 seconds — location changes frequently
  });
}

// ---- Geofences ----

export function useGeofences(groupId: string) {
  return useQuery<Geofence[]>({
    queryKey: KEYS.geofences(groupId),
    queryFn: () =>
      apiClient.get<Geofence[]>(`/api/v1/location/geofences?group_id=${groupId}`),
    enabled: Boolean(groupId),
  });
}

export interface CreateGeofencePayload {
  group_id: string;
  name: string;
  lat: number;
  lng: number;
  radius_meters: number;
  type: GeofenceType;
  alerts_enabled?: boolean;
}

export function useCreateGeofence() {
  const queryClient = useQueryClient();
  return useMutation<Geofence, Error, CreateGeofencePayload>({
    mutationFn: (payload) =>
      apiClient.post<Geofence>('/api/v1/location/geofences', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['location', 'geofences'] });
    },
  });
}

export interface UpdateGeofencePayload {
  geofenceId: string;
  name?: string;
  radius_meters?: number;
  alerts_enabled?: boolean;
}

export function useUpdateGeofence() {
  const queryClient = useQueryClient();
  return useMutation<Geofence, Error, UpdateGeofencePayload>({
    mutationFn: ({ geofenceId, ...body }) =>
      apiClient.put<Geofence>(`/api/v1/location/geofences/${geofenceId}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['location', 'geofences'] });
    },
  });
}

export function useDeleteGeofence() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (geofenceId) =>
      apiClient.delete<void>(`/api/v1/location/geofences/${geofenceId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['location', 'geofences'] });
    },
  });
}

// ---- Location settings ----

export function useLocationSettings(memberId: string) {
  return useQuery<LocationSettings>({
    queryKey: KEYS.settings(memberId),
    queryFn: () =>
      apiClient.get<LocationSettings>(`/api/v1/location/settings?member_id=${memberId}`),
    enabled: Boolean(memberId),
  });
}

export interface UpdateLocationSettingsPayload {
  memberId: string;
  tracking_enabled?: boolean;
  history_retention_days?: number;
}

export function useUpdateLocationSettings() {
  const queryClient = useQueryClient();
  return useMutation<LocationSettings, Error, UpdateLocationSettingsPayload>({
    mutationFn: ({ memberId, ...body }) =>
      apiClient.put<LocationSettings>(`/api/v1/location/settings?member_id=${memberId}`, body),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: KEYS.settings(variables.memberId) });
    },
  });
}
