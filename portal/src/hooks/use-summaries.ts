"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, api } from "@/lib/api-client";
import type { ConversationSummary, PaginatedResponse } from "@/types";

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== ""
  );
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");
}

export const summaryKeys = {
  all: ["summaries"] as const,
  lists: () => [...summaryKeys.all, "list"] as const,
  list: (params?: Record<string, unknown>) =>
    [...summaryKeys.lists(), params] as const,
  detail: (summaryId: string) =>
    [...summaryKeys.all, "detail", summaryId] as const,
};

export function useSummaries(params?: {
  member_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery<PaginatedResponse<ConversationSummary>>({
    queryKey: summaryKeys.list(params),
    queryFn: () =>
      apiFetch(
        `/api/v1/capture/summaries${qs({
          member_id: params?.member_id,
          start_date: params?.start_date,
          end_date: params?.end_date,
          page: params?.page,
          page_size: params?.page_size,
        })}`
      ),
    enabled: !!params?.member_id,
  });
}

export function useSummary(summaryId: string) {
  return useQuery<ConversationSummary>({
    queryKey: summaryKeys.detail(summaryId),
    queryFn: () => apiFetch(`/api/v1/capture/summaries/${summaryId}`),
    enabled: !!summaryId,
  });
}

export function useTriggerSummarization() {
  const queryClient = useQueryClient();

  return useMutation<
    ConversationSummary,
    Error,
    { event_id: string; member_age?: number }
  >({
    mutationFn: (data) => api.post("/api/v1/capture/summarize", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: summaryKeys.all });
    },
  });
}
