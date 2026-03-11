"use client";

import { useQuery } from "@tanstack/react-query";
import { riskApi } from "@/lib/api-client";
import type { DeepfakeGuidance } from "@/types";

export function useDeepfakeGuidance(enabled = true) {
  return useQuery<DeepfakeGuidance>({
    queryKey: ["deepfake-guidance"],
    queryFn: () => riskApi.getDeepfakeGuidance(),
    enabled,
    staleTime: 1000 * 60 * 60, // cache for 1 hour — content rarely changes
  });
}
