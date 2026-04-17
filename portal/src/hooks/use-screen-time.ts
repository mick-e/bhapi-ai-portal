"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface AppUsage {
  app_name: string;
  category: string;
  minutes_today: number;
  minutes_limit: number | null;
  member_id: string;
  member_name: string;
}

export interface ScreenTimeLimit {
  id: string;
  member_id: string;
  app_name: string | null;
  category: string | null;
  daily_minutes: number;
  active: boolean;
  created_at: string;
}

export interface ScreenTimeSchedule {
  id: string;
  member_id: string;
  member_name: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  label: string;
  active: boolean;
}

export interface ExtensionRequest {
  id: string;
  member_id: string;
  member_name: string;
  requested_minutes: number;
  reason: string;
  status: "pending" | "approved" | "denied";
  created_at: string;
  decided_at: string | null;
}

// ─── Query Keys ─────────────────────────────────────────────────────────────

export const screenTimeKeys = {
  all: ["screen-time"] as const,
  usage: () => [...screenTimeKeys.all, "usage"] as const,
  limits: () => [...screenTimeKeys.all, "limits"] as const,
  schedules: () => [...screenTimeKeys.all, "schedules"] as const,
  requests: () => [...screenTimeKeys.all, "requests"] as const,
};

// ─── Queries ────────────────────────────────────────────────────────────────

export function useScreenTimeUsage() {
  return useQuery<AppUsage[]>({
    queryKey: screenTimeKeys.usage(),
    queryFn: () => apiFetch<AppUsage[]>("/api/v1/screen-time/usage"),
  });
}

export function useScreenTimeLimits() {
  return useQuery<ScreenTimeLimit[]>({
    queryKey: screenTimeKeys.limits(),
    queryFn: () => apiFetch<ScreenTimeLimit[]>("/api/v1/screen-time/limits"),
  });
}

export function useScreenTimeSchedules() {
  return useQuery<ScreenTimeSchedule[]>({
    queryKey: screenTimeKeys.schedules(),
    queryFn: () => apiFetch<ScreenTimeSchedule[]>("/api/v1/screen-time/schedules"),
  });
}

export function useExtensionRequests() {
  return useQuery<ExtensionRequest[]>({
    queryKey: screenTimeKeys.requests(),
    queryFn: () => apiFetch<ExtensionRequest[]>("/api/v1/screen-time/requests"),
  });
}

// ─── Mutations ──────────────────────────────────────────────────────────────

export function useCreateLimit() {
  const queryClient = useQueryClient();

  return useMutation<
    ScreenTimeLimit,
    Error,
    { member_id: string; app_name?: string; category?: string; daily_minutes: number }
  >({
    mutationFn: (data) =>
      apiFetch<ScreenTimeLimit>("/api/v1/screen-time/limits", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: screenTimeKeys.limits() });
    },
  });
}

export function useDeleteLimit() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (limitId) =>
      apiFetch<void>(`/api/v1/screen-time/limits/${limitId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: screenTimeKeys.limits() });
    },
  });
}

export function useDecideExtensionRequest() {
  const queryClient = useQueryClient();

  return useMutation<
    ExtensionRequest,
    Error,
    { requestId: string; decision: "approved" | "denied" }
  >({
    mutationFn: ({ requestId, decision }) =>
      apiFetch<ExtensionRequest>(`/api/v1/screen-time/requests/${requestId}`, {
        method: "PUT",
        body: JSON.stringify({ status: decision }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: screenTimeKeys.requests() });
    },
  });
}
