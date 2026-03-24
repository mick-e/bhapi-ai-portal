"use client";

import { useQueries } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { CaptureEvent, Alert, PaginatedResponse } from "@/types";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface RiskScoreSummary {
  score: number;
  trend: "up" | "down" | "stable";
  confidence: "low" | "medium" | "high";
  factors: string[];
}

export interface AIActivitySummary {
  events_today: number;
  top_platforms: string[];
  recent_events: CaptureEvent[];
}

export interface SocialSummary {
  posts_today: number;
  comments_today: number;
  friend_requests_pending: number;
}

export interface ScreenTimeSummary {
  total_minutes_today: number;
  top_categories: Array<{ category: string; minutes: number }>;
}

export interface LocationSummary {
  last_known_location: string | null;
  geofence_status: "inside" | "outside" | "unknown";
  last_updated: string | null;
}

export interface ActionCenter {
  pending_approvals: number;
  unread_alerts: number;
  pending_extension_requests: number;
}

export interface UnifiedDashboardData {
  childId: string;
  riskScore: RiskScoreSummary | null;
  aiActivity: AIActivitySummary | null;
  social: SocialSummary | null;
  screenTime: ScreenTimeSummary | null;
  location: LocationSummary | null;
  actionCenter: ActionCenter | null;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const unifiedDashboardKeys = {
  all: ["unified-dashboard"] as const,
  child: (childId: string) => [...unifiedDashboardKeys.all, childId] as const,
  riskScore: (childId: string) =>
    [...unifiedDashboardKeys.child(childId), "risk-score"] as const,
  aiActivity: (childId: string) =>
    [...unifiedDashboardKeys.child(childId), "ai-activity"] as const,
  social: (childId: string) =>
    [...unifiedDashboardKeys.child(childId), "social"] as const,
  screenTime: (childId: string) =>
    [...unifiedDashboardKeys.child(childId), "screen-time"] as const,
  location: (childId: string) =>
    [...unifiedDashboardKeys.child(childId), "location"] as const,
  actionCenter: (childId: string) =>
    [...unifiedDashboardKeys.child(childId), "action-center"] as const,
};

// ─── API fetchers ─────────────────────────────────────────────────────────────

async function fetchRiskScore(childId: string): Promise<RiskScoreSummary> {
  return api.get<RiskScoreSummary>(
    `/api/v1/risk/score?member_id=${encodeURIComponent(childId)}`
  );
}

async function fetchAIActivity(childId: string): Promise<AIActivitySummary> {
  const data = await api.get<PaginatedResponse<CaptureEvent>>(
    `/api/v1/capture/events?member_id=${encodeURIComponent(childId)}&page_size=5`
  );
  const events = data.items ?? [];
  const platformCounts: Record<string, number> = {};
  events.forEach((e) => {
    platformCounts[e.provider] = (platformCounts[e.provider] ?? 0) + 1;
  });
  const topPlatforms = Object.entries(platformCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([p]) => p);
  return {
    events_today: data.total ?? 0,
    top_platforms: topPlatforms,
    recent_events: events.slice(0, 5),
  };
}

async function fetchSocialSummary(childId: string): Promise<SocialSummary> {
  return api.get<SocialSummary>(
    `/api/v1/social/summary?member_id=${encodeURIComponent(childId)}`
  );
}

async function fetchScreenTime(childId: string): Promise<ScreenTimeSummary> {
  return api.get<ScreenTimeSummary>(
    `/api/v1/screen-time/summary?member_id=${encodeURIComponent(childId)}`
  );
}

async function fetchLocation(childId: string): Promise<LocationSummary> {
  return api.get<LocationSummary>(
    `/api/v1/location/last?member_id=${encodeURIComponent(childId)}`
  );
}

async function fetchActionCenter(childId: string): Promise<ActionCenter> {
  const [alerts, approvals] = await Promise.all([
    api.get<PaginatedResponse<Alert>>(
      `/api/v1/alerts?read=false&page_size=1`
    ),
    api.get<{ items: unknown[]; total: number }>(
      `/api/v1/blocking/pending-approvals?member_id=${encodeURIComponent(childId)}`
    ).catch(() => ({ items: [], total: 0 })),
  ]);
  return {
    pending_approvals: (approvals as { items: unknown[]; total: number }).total ?? 0,
    unread_alerts: alerts.total ?? 0,
    pending_extension_requests: 0,
  };
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export interface UseUnifiedDashboardResult {
  data: UnifiedDashboardData;
  isLoading: boolean;
  isError: boolean;
  errors: (Error | null)[];
  refetchAll: () => void;
}

export function useUnifiedDashboard(childId: string): UseUnifiedDashboardResult {
  const enabled = Boolean(childId);

  const results = useQueries({
    queries: [
      {
        queryKey: unifiedDashboardKeys.riskScore(childId),
        queryFn: () => fetchRiskScore(childId),
        enabled,
        retry: 1,
      },
      {
        queryKey: unifiedDashboardKeys.aiActivity(childId),
        queryFn: () => fetchAIActivity(childId),
        enabled,
        retry: 1,
      },
      {
        queryKey: unifiedDashboardKeys.social(childId),
        queryFn: () => fetchSocialSummary(childId),
        enabled,
        retry: 1,
      },
      {
        queryKey: unifiedDashboardKeys.screenTime(childId),
        queryFn: () => fetchScreenTime(childId),
        enabled,
        retry: 1,
      },
      {
        queryKey: unifiedDashboardKeys.location(childId),
        queryFn: () => fetchLocation(childId),
        enabled,
        retry: 1,
      },
      {
        queryKey: unifiedDashboardKeys.actionCenter(childId),
        queryFn: () => fetchActionCenter(childId),
        enabled,
        retry: 1,
      },
    ],
  });

  const [riskResult, aiResult, socialResult, screenResult, locResult, actionResult] = results;

  const isLoading = results.some((r) => r.isLoading);
  const isError = results.some((r) => r.isError);
  const errors = results.map((r) => r.error as Error | null);

  const data: UnifiedDashboardData = {
    childId,
    riskScore: (riskResult.data as RiskScoreSummary) ?? null,
    aiActivity: (aiResult.data as AIActivitySummary) ?? null,
    social: (socialResult.data as SocialSummary) ?? null,
    screenTime: (screenResult.data as ScreenTimeSummary) ?? null,
    location: (locResult.data as LocationSummary) ?? null,
    actionCenter: (actionResult.data as ActionCenter) ?? null,
  };

  function refetchAll() {
    results.forEach((r) => r.refetch());
  }

  return { data, isLoading, isError, errors, refetchAll };
}
