"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { reportsApi } from "@/lib/api-client";
import type {
  Report,
  PaginatedResponse,
  CreateReportRequest,
  ReportScheduleConfig,
} from "@/types";

export const reportKeys = {
  all: ["reports"] as const,
  lists: () => [...reportKeys.all, "list"] as const,
  list: (params?: Record<string, unknown>) =>
    [...reportKeys.lists(), params] as const,
  schedules: () => [...reportKeys.all, "schedules"] as const,
};

export function useReports(params?: {
  page?: number;
  page_size?: number;
  type?: string;
  status?: string;
}) {
  return useQuery<PaginatedResponse<Report>>({
    queryKey: reportKeys.list(params),
    queryFn: () => reportsApi.list(params),
  });
}

export function useReportSchedules() {
  return useQuery<ReportScheduleConfig[]>({
    queryKey: reportKeys.schedules(),
    queryFn: () => reportsApi.getSchedules(),
  });
}

export function useCreateReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateReportRequest) => reportsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: reportKeys.lists() });
    },
  });
}

export function useDownloadReport() {
  return useMutation({
    mutationFn: async (reportId: string) => {
      const blob = await reportsApi.download(reportId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report-${reportId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  });
}

export function useUpdateReportSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ReportScheduleConfig) =>
      reportsApi.updateSchedule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: reportKeys.schedules() });
    },
  });
}
