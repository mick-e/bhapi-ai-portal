"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { PaginatedResponse, PanicReport, PanicReportCreate } from "@/types";

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");
}

export const panicKeys = {
  all: ["panic"] as const,
  list: (groupId: string) => [...panicKeys.all, "list", groupId] as const,
  quickResponses: ["panic", "quick-responses"] as const,
};

export function usePanicReports(
  groupId: string | null,
  page: number = 1,
  pageSize: number = 20
) {
  return useQuery<PaginatedResponse<PanicReport>>({
    queryKey: [...panicKeys.list(groupId || ""), page],
    queryFn: () =>
      api.get<PaginatedResponse<PanicReport>>(
        `/api/v1/alerts/panic${qs({
          group_id: groupId!,
          page,
          page_size: pageSize,
        })}`
      ),
    enabled: !!groupId,
  });
}

export function useCreatePanicReport() {
  const queryClient = useQueryClient();

  return useMutation<PanicReport, Error, PanicReportCreate>({
    mutationFn: (data) => api.post<PanicReport>("/api/v1/alerts/panic", data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: panicKeys.list(variables.group_id),
      });
    },
  });
}

export function useRespondToPanic() {
  const queryClient = useQueryClient();

  return useMutation<
    PanicReport,
    Error,
    { reportId: string; response: string; groupId: string }
  >({
    mutationFn: ({ reportId, response }) =>
      api.post<PanicReport>(`/api/v1/alerts/panic/${reportId}/respond`, {
        response,
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: panicKeys.list(variables.groupId),
      });
    },
  });
}

export function useQuickResponses() {
  return useQuery<{ responses: string[] }>({
    queryKey: panicKeys.quickResponses,
    queryFn: () =>
      api.get<{ responses: string[] }>("/api/v1/alerts/panic/quick-responses"),
  });
}
