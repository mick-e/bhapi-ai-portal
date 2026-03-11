"use client";

import { useQuery } from "@tanstack/react-query";
import { platformSafetyApi } from "@/lib/api-client";
import type { PlatformSafetyRating, PlatformSafetyRecommendation } from "@/types";

export const platformSafetyKeys = {
  all: ["platform-safety"] as const,
  list: () => [...platformSafetyKeys.all, "all"] as const,
  detail: (platform: string) => [...platformSafetyKeys.all, "detail", platform] as const,
  recommendations: (age: number) => [...platformSafetyKeys.all, "recommend", age] as const,
};

export function usePlatformSafetyRatings(enabled = true) {
  return useQuery<{ platforms: PlatformSafetyRating[] }>({
    queryKey: platformSafetyKeys.list(),
    queryFn: () => platformSafetyApi.getAll(),
    enabled,
  });
}

export function usePlatformSafetyRating(platform: string) {
  return useQuery<PlatformSafetyRating>({
    queryKey: platformSafetyKeys.detail(platform),
    queryFn: () => platformSafetyApi.getOne(platform),
    enabled: !!platform,
  });
}

export function usePlatformSafetyRecommendations(age: number | null) {
  return useQuery<{ platforms: PlatformSafetyRecommendation[] }>({
    queryKey: platformSafetyKeys.recommendations(age!),
    queryFn: () => platformSafetyApi.getRecommendations(age!),
    enabled: age !== null,
  });
}
