"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { complianceApi } from "@/lib/api-client";
import type { AppealRecord, TransparencyReport } from "@/types";

export const complianceKeys = {
  all: ["compliance"] as const,
  transparency: (groupId: string) =>
    [...complianceKeys.all, "transparency", groupId] as const,
  appeals: (groupId: string) =>
    [...complianceKeys.all, "appeals", groupId] as const,
};

export function useTransparencyReport(groupId: string | null) {
  return useQuery<TransparencyReport>({
    queryKey: complianceKeys.transparency(groupId || ""),
    queryFn: () => complianceApi.transparency(groupId!),
    enabled: !!groupId,
  });
}

export function useAppeals(groupId: string | null) {
  return useQuery<{ items: AppealRecord[]; total: number }>({
    queryKey: complianceKeys.appeals(groupId || ""),
    queryFn: () => complianceApi.listAppeals(groupId!),
    enabled: !!groupId,
  });
}

export function useSubmitAppeal() {
  const queryClient = useQueryClient();

  return useMutation<
    AppealRecord,
    Error,
    { riskEventId: string; group_id: string; reason: string }
  >({
    mutationFn: ({ riskEventId, ...data }) =>
      complianceApi.submitAppeal(riskEventId, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: complianceKeys.appeals(variables.group_id),
      });
    },
  });
}
