"use client";

import { useQuery } from "@tanstack/react-query";
import { activityApi } from "@/lib/api-client";
import type { CaptureEvent, PaginatedResponse } from "@/types";

export const activityKeys = {
  all: ["activity"] as const,
  lists: () => [...activityKeys.all, "list"] as const,
  list: (params?: Record<string, unknown>) =>
    [...activityKeys.lists(), params] as const,
  detail: (eventId: string) =>
    [...activityKeys.all, "detail", eventId] as const,
};

export function useActivity(params?: {
  page?: number;
  page_size?: number;
  member_id?: string;
  risk_level?: string;
  provider?: string;
  event_type?: string;
  search?: string;
  start_date?: string;
  end_date?: string;
}) {
  return useQuery<PaginatedResponse<CaptureEvent>>({
    queryKey: activityKeys.list(params),
    queryFn: () => activityApi.list(params),
    refetchInterval: 15_000, // refresh every 15 seconds
  });
}

export function useActivityEvent(eventId: string) {
  return useQuery<CaptureEvent>({
    queryKey: activityKeys.detail(eventId),
    queryFn: () => activityApi.get(eventId),
    enabled: !!eventId,
  });
}
