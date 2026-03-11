"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { DependencyScore, DependencyHistoryResponse } from "@/types";

export const dependencyKeys = {
  all: ["dependency"] as const,
  score: (memberId: string, days?: number) =>
    [...dependencyKeys.all, "score", memberId, days] as const,
  history: (memberId: string, days?: number) =>
    [...dependencyKeys.all, "history", memberId, days] as const,
};

export function useDependencyScore(memberId: string, days = 30) {
  return useQuery<DependencyScore>({
    queryKey: dependencyKeys.score(memberId, days),
    queryFn: () =>
      apiFetch(`/api/v1/risk/dependency-score?member_id=${memberId}&days=${days}`),
    enabled: !!memberId,
    refetchInterval: 60_000,
  });
}

export function useDependencyHistory(memberId: string, days = 90) {
  return useQuery<DependencyHistoryResponse>({
    queryKey: dependencyKeys.history(memberId, days),
    queryFn: () =>
      apiFetch(
        `/api/v1/risk/dependency-score/history?member_id=${memberId}&days=${days}`
      ),
    enabled: !!memberId,
  });
}
