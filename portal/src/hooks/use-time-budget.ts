"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { TimeBudget, TimeBudgetUpdate, TimeBudgetUsageItem, BedtimeConfig, BedtimeUpdate } from "@/types";

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");
}

export const timeBudgetKeys = {
  all: ["time-budget"] as const,
  budget: (groupId: string, memberId: string) =>
    [...timeBudgetKeys.all, "budget", groupId, memberId] as const,
  history: (groupId: string, memberId: string) =>
    [...timeBudgetKeys.all, "history", groupId, memberId] as const,
  bedtime: (groupId: string, memberId: string) =>
    [...timeBudgetKeys.all, "bedtime", groupId, memberId] as const,
};

export function useTimeBudget(groupId: string | null, memberId: string) {
  return useQuery<TimeBudget>({
    queryKey: timeBudgetKeys.budget(groupId || "", memberId),
    queryFn: () =>
      api.get<TimeBudget>(
        `/api/v1/blocking/time-budget/${memberId}${qs({ group_id: groupId! })}`
      ),
    enabled: !!groupId && !!memberId,
  });
}

export function useUpdateTimeBudget() {
  const queryClient = useQueryClient();

  return useMutation<
    TimeBudget,
    Error,
    { groupId: string; memberId: string; data: TimeBudgetUpdate }
  >({
    mutationFn: ({ groupId, memberId, data }) =>
      api.put<TimeBudget>(
        `/api/v1/blocking/time-budget/${memberId}${qs({ group_id: groupId })}`,
        data
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: timeBudgetKeys.budget(variables.groupId, variables.memberId),
      });
    },
  });
}

export function useTimeBudgetHistory(
  groupId: string | null,
  memberId: string,
  days: number = 7
) {
  return useQuery<TimeBudgetUsageItem[]>({
    queryKey: timeBudgetKeys.history(groupId || "", memberId),
    queryFn: () =>
      api.get<TimeBudgetUsageItem[]>(
        `/api/v1/blocking/time-budget/${memberId}/history${qs({
          group_id: groupId!,
          days,
        })}`
      ),
    enabled: !!groupId && !!memberId,
  });
}

// ─── Bedtime Mode hooks ──────────────────────────────────────────────────────

export function useBedtimeMode(groupId: string | null, memberId: string) {
  return useQuery<BedtimeConfig>({
    queryKey: timeBudgetKeys.bedtime(groupId || "", memberId),
    queryFn: () =>
      api.get<BedtimeConfig>(
        `/api/v1/blocking/bedtime/${memberId}${qs({ group_id: groupId! })}`
      ),
    enabled: !!groupId && !!memberId,
  });
}

export function useUpdateBedtime() {
  const queryClient = useQueryClient();

  return useMutation<
    BedtimeConfig,
    Error,
    { groupId: string; memberId: string; data: BedtimeUpdate }
  >({
    mutationFn: ({ groupId, memberId, data }) =>
      api.put<BedtimeConfig>(
        `/api/v1/blocking/bedtime/${memberId}${qs({ group_id: groupId })}`,
        data
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: timeBudgetKeys.bedtime(variables.groupId, variables.memberId),
      });
    },
  });
}

export function useDeleteBedtime() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { groupId: string; memberId: string }>({
    mutationFn: ({ groupId, memberId }) =>
      api.delete<void>(
        `/api/v1/blocking/bedtime/${memberId}${qs({ group_id: groupId })}`
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: timeBudgetKeys.bedtime(variables.groupId, variables.memberId),
      });
    },
  });
}
