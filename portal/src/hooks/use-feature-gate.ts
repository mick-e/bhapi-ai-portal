"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

interface FeatureSummary {
  plan: string;
  member_limit: number | null;
  platform_limit: number | null;
  features: Record<string, boolean>;
}

export function useFeatureGate() {
  return useQuery<FeatureSummary>({
    queryKey: ["feature-gate"],
    queryFn: () => api.get<FeatureSummary>("/api/v1/billing/features"),
    staleTime: 120_000,
  });
}

export function useFeatureCheck(feature: string) {
  const { data, isLoading } = useFeatureGate();
  return {
    enabled: data?.features?.[feature] ?? false,
    plan: data?.plan ?? "free",
    isLoading,
  };
}
