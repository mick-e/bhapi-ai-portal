"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api-client";
import type { DashboardData } from "@/types";

export const dashboardKeys = {
  all: ["dashboard"] as const,
  summary: () => [...dashboardKeys.all, "summary"] as const,
};

export function useDashboardSummary() {
  return useQuery<DashboardData>({
    queryKey: dashboardKeys.summary(),
    queryFn: () => dashboardApi.getSummary(),
    refetchInterval: 30_000, // refresh every 30 seconds
  });
}
