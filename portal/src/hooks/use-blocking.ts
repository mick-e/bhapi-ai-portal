"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { blockingApi } from "@/lib/api-client";
import type { BlockRule, BlockStatus } from "@/types";

export const blockingKeys = {
  all: ["blocking"] as const,
  rules: (groupId: string) => [...blockingKeys.all, "rules", groupId] as const,
  check: (groupId: string, memberId: string) =>
    [...blockingKeys.all, "check", groupId, memberId] as const,
};

export function useBlockRules(groupId: string | null) {
  return useQuery<BlockRule[]>({
    queryKey: blockingKeys.rules(groupId || ""),
    queryFn: () => blockingApi.list(groupId!),
    enabled: !!groupId,
  });
}

export function useBlockCheck(groupId: string | null, memberId: string) {
  return useQuery<BlockStatus>({
    queryKey: blockingKeys.check(groupId || "", memberId),
    queryFn: () => blockingApi.check(groupId!, memberId),
    enabled: !!groupId && !!memberId,
  });
}

export function useCreateBlockRule() {
  const queryClient = useQueryClient();

  return useMutation<
    BlockRule,
    Error,
    { group_id: string; member_id: string; platforms?: string[]; reason?: string }
  >({
    mutationFn: (data) => blockingApi.create(data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: blockingKeys.rules(variables.group_id),
      });
    },
  });
}

export function useRevokeBlockRule() {
  const queryClient = useQueryClient();

  return useMutation<BlockRule, Error, { ruleId: string; groupId: string }>({
    mutationFn: ({ ruleId }) => blockingApi.revoke(ruleId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: blockingKeys.rules(variables.groupId),
      });
    },
  });
}
