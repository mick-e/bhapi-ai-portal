"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { rewardsApi, deviceApi } from "@/lib/api-client";
import { useAuth } from "@/hooks/use-auth";
import type { RewardItem, DeviceSessionSummary } from "@/types";

export const rewardKeys = {
  all: ["rewards"] as const,
  list: (groupId: string, memberId: string) =>
    [...rewardKeys.all, "list", groupId, memberId] as const,
};

export const deviceKeys = {
  all: ["devices"] as const,
  summary: (memberId: string, date?: string) =>
    [...deviceKeys.all, "summary", memberId, date] as const,
};

export function useRewards(memberId: string) {
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useQuery<RewardItem[]>({
    queryKey: rewardKeys.list(groupId, memberId),
    queryFn: () => rewardsApi.list(groupId, memberId),
    enabled: !!groupId && !!memberId,
  });
}

export function useCheckRewards() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useMutation({
    mutationFn: (memberId: string) =>
      rewardsApi.checkTriggers(groupId, memberId),
    onSuccess: (_data, memberId) => {
      queryClient.invalidateQueries({
        queryKey: rewardKeys.list(groupId, memberId),
      });
    },
  });
}

export function useDeviceSummary(memberId: string, date?: string) {
  return useQuery<DeviceSessionSummary>({
    queryKey: deviceKeys.summary(memberId, date),
    queryFn: () => deviceApi.getSessionSummary(memberId, date),
    enabled: !!memberId,
  });
}
