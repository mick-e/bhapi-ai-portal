"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { spendApi } from "@/lib/api-client";
import type { SpendSummary, SpendRecord, BudgetThreshold, PaginatedResponse } from "@/types";

export const spendKeys = {
  all: ["spend"] as const,
  summaries: () => [...spendKeys.all, "summary"] as const,
  summary: (period?: string) => [...spendKeys.summaries(), period] as const,
  records: () => [...spendKeys.all, "records"] as const,
  recordList: (params?: Record<string, unknown>) =>
    [...spendKeys.records(), params] as const,
};

export function useSpendSummary(period?: "day" | "week" | "month") {
  return useQuery<SpendSummary>({
    queryKey: spendKeys.summary(period),
    queryFn: () => spendApi.getSummary(period),
  });
}

export function useSpendRecords(params?: {
  page?: number;
  page_size?: number;
  member_id?: string;
  provider?: string;
}) {
  return useQuery<PaginatedResponse<SpendRecord>>({
    queryKey: spendKeys.recordList(params),
    queryFn: () => spendApi.getRecords(params),
  });
}

export function useBudgetThresholds() {
  return useQuery<BudgetThreshold[]>({
    queryKey: [...spendKeys.all, "thresholds"] as const,
    queryFn: () => spendApi.getThresholds(),
  });
}

export function useCreateBudgetThreshold() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      group_id: string;
      member_id?: string | null;
      type: "soft" | "hard";
      amount: number;
      notify_at?: number[];
    }) => spendApi.createThreshold(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: spendKeys.all });
    },
  });
}
