"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { alertsApi, riskApi } from "@/lib/api-client";
import type {
  Alert,
  RiskEvent,
  PaginatedResponse,
  AcknowledgeRiskRequest,
} from "@/types";

export const alertKeys = {
  all: ["alerts"] as const,
  lists: () => [...alertKeys.all, "list"] as const,
  list: (params?: Record<string, unknown>) =>
    [...alertKeys.lists(), params] as const,
};

export const riskKeys = {
  all: ["risk"] as const,
  lists: () => [...riskKeys.all, "list"] as const,
  list: (params?: Record<string, unknown>) =>
    [...riskKeys.lists(), params] as const,
};

export function useAlerts(params?: {
  page?: number;
  page_size?: number;
  severity?: string;
  type?: string;
  read?: boolean;
  start_date?: string;
  end_date?: string;
}) {
  return useQuery<PaginatedResponse<Alert>>({
    queryKey: alertKeys.list(params),
    queryFn: () => alertsApi.list(params),
    refetchInterval: 15_000,
  });
}

export function useRiskEvents(params?: {
  page?: number;
  page_size?: number;
  severity?: string;
  category?: string;
  resolved?: boolean;
  member_id?: string;
}) {
  return useQuery<PaginatedResponse<RiskEvent>>({
    queryKey: riskKeys.list(params),
    queryFn: () => riskApi.list(params),
    refetchInterval: 15_000,
  });
}

export function useMarkAlertRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (alertId: string) => alertsApi.markRead(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.lists() });
    },
  });
}

export function useMarkAlertActioned() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (alertId: string) => alertsApi.markActioned(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.lists() });
    },
  });
}

export function useMarkAllAlertsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => alertsApi.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.lists() });
    },
  });
}

export function useSnoozeAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ alertId, hours }: { alertId: string; hours: number }) =>
      alertsApi.snooze(alertId, hours),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.lists() });
    },
  });
}

export function useAcknowledgeRisk() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AcknowledgeRiskRequest) => riskApi.acknowledge(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riskKeys.lists() });
      queryClient.invalidateQueries({ queryKey: alertKeys.lists() });
    },
  });
}
