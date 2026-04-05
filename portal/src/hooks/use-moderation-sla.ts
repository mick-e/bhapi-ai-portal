"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

export interface SLAMetrics {
  pre_publish_p50_ms: number;
  pre_publish_p95_ms: number;
  post_publish_p50_ms: number;
  post_publish_p95_ms: number;
  queue_depth: number;
  oldest_pending_age_seconds: number;
  sla_breach_count_24h: number;
  total_reviewed_24h: number;
}

export const moderationSlaKeys = {
  all: ["moderation-sla"] as const,
  live: () => [...moderationSlaKeys.all, "live"] as const,
};

export function useModerationSla() {
  return useQuery<SLAMetrics>({
    queryKey: moderationSlaKeys.live(),
    queryFn: () => api.get<SLAMetrics>("/api/v1/moderation/sla/live"),
    refetchInterval: 10_000,
    staleTime: 5_000,
  });
}
