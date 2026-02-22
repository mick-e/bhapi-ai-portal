"use client";

import { useQuery } from "@tanstack/react-query";
import { spendApi } from "@/lib/api-client";
import type { SpendSummary, SpendRecord, PaginatedResponse } from "@/types";

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
