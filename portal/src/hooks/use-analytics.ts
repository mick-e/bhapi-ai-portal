"use client";

import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api-client";
import type {
  AnomalyResponse,
  MemberBaseline,
  PeerComparisonResponse,
  TrendData,
  UsagePattern,
} from "@/types";

export const analyticsKeys = {
  all: ["analytics"] as const,
  trends: (groupId: string, days: number) =>
    [...analyticsKeys.all, "trends", groupId, days] as const,
  usage: (groupId: string, days: number) =>
    [...analyticsKeys.all, "usage", groupId, days] as const,
  baselines: (groupId: string, days: number) =>
    [...analyticsKeys.all, "baselines", groupId, days] as const,
  anomalies: (groupId: string) =>
    [...analyticsKeys.all, "anomalies", groupId] as const,
  peerComparison: (groupId: string, days: number) =>
    [...analyticsKeys.all, "peer-comparison", groupId, days] as const,
};

export function useTrends(groupId: string | null, days = 7) {
  return useQuery<TrendData>({
    queryKey: analyticsKeys.trends(groupId || "", days),
    queryFn: () => analyticsApi.trends(groupId!, days),
    enabled: !!groupId,
  });
}

export function useUsagePatterns(groupId: string | null, days = 7) {
  return useQuery<UsagePattern>({
    queryKey: analyticsKeys.usage(groupId || "", days),
    queryFn: () => analyticsApi.usagePatterns(groupId!, days),
    enabled: !!groupId,
  });
}

export function useMemberBaselines(groupId: string | null, days = 30) {
  return useQuery<MemberBaseline[]>({
    queryKey: analyticsKeys.baselines(groupId || "", days),
    queryFn: () => analyticsApi.memberBaselines(groupId!, days),
    enabled: !!groupId,
  });
}

export function useAnomalies(groupId: string | null) {
  return useQuery<AnomalyResponse>({
    queryKey: analyticsKeys.anomalies(groupId || ""),
    queryFn: () => analyticsApi.anomalies(groupId!),
    enabled: !!groupId,
  });
}

export function usePeerComparison(groupId: string | null, days = 30) {
  return useQuery<PeerComparisonResponse>({
    queryKey: analyticsKeys.peerComparison(groupId || "", days),
    queryFn: () => analyticsApi.peerComparison(groupId!, days),
    enabled: !!groupId,
  });
}
