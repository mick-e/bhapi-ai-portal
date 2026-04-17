"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface Geofence {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  member_id: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LocationHistory {
  id: string;
  member_id: string;
  latitude: number;
  longitude: number;
  accuracy_meters: number;
  timestamp: string;
  geofence_id: string | null;
  event_type: string;
}

export interface SchoolCheckIn {
  id: string;
  member_id: string;
  member_name: string;
  school_name: string;
  checked_in_at: string;
  checked_out_at: string | null;
  status: string;
}

export interface LocationAuditEntry {
  id: string;
  action: string;
  actor_id: string;
  target_member_id: string;
  details: string;
  timestamp: string;
}

// ─── Query Keys ─────────────────────────────────────────────────────────────

export const locationKeys = {
  all: ["location"] as const,
  geofences: () => [...locationKeys.all, "geofences"] as const,
  history: (memberId?: string) =>
    [...locationKeys.all, "history", memberId ?? "all"] as const,
  checkIns: () => [...locationKeys.all, "check-ins"] as const,
  audit: () => [...locationKeys.all, "audit"] as const,
};

// ─── Queries ────────────────────────────────────────────────────────────────

export function useGeofences() {
  return useQuery<Geofence[]>({
    queryKey: locationKeys.geofences(),
    queryFn: () => apiFetch<Geofence[]>("/api/v1/location/geofences"),
  });
}

export function useLocationHistory(memberId?: string) {
  const path = memberId
    ? `/api/v1/location/history?member_id=${encodeURIComponent(memberId)}`
    : "/api/v1/location/history";
  return useQuery<LocationHistory[]>({
    queryKey: locationKeys.history(memberId),
    queryFn: () => apiFetch<LocationHistory[]>(path),
  });
}

export function useSchoolCheckIns() {
  return useQuery<SchoolCheckIn[]>({
    queryKey: locationKeys.checkIns(),
    queryFn: () => apiFetch<SchoolCheckIn[]>("/api/v1/location/check-ins"),
  });
}

// ─── Mutations ──────────────────────────────────────────────────────────────

export function useCreateGeofence() {
  const queryClient = useQueryClient();

  return useMutation<
    Geofence,
    Error,
    { name: string; latitude: number; longitude: number; radius_meters: number; member_id: string }
  >({
    mutationFn: (data) =>
      apiFetch<Geofence>("/api/v1/location/geofences", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: locationKeys.geofences() });
    },
  });
}

export function useDeleteGeofence() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (geofenceId) =>
      apiFetch<void>(`/api/v1/location/geofences/${geofenceId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: locationKeys.geofences() });
    },
  });
}
