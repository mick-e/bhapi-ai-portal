"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ApiClient {
  id: string;
  name: string;
  client_id: string;
  is_active: boolean;
  is_approved: boolean;
  created_at: string;
}

export interface ApiClientListResponse {
  items: ApiClient[];
  total: number;
}

export interface UsageDay {
  date: string;
  calls: number;
}

export interface ApiUsageResponse {
  total_calls: number;
  tier_name: string;
  tier_limit: number;
  days: UsageDay[];
}

export interface WebhookEndpoint {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
}

export interface WebhookEndpointListResponse {
  items: WebhookEndpoint[];
  total: number;
}

export interface CreateWebhookInput {
  url: string;
  events: string[];
  secret?: string;
}

export interface WebhookDelivery {
  id: string;
  event_type: string;
  response_status: number | null;
  success: boolean;
  created_at: string;
}

export interface WebhookDeliveryResponse {
  id: string;
  event_type: string;
  response_status: number | null;
  success: boolean;
  created_at: string;
}

// ─── Query Keys ──────────────────────────────────────────────────────────────

export const developerKeys = {
  all: ["developer-portal"] as const,
  clients: () => [...developerKeys.all, "clients"] as const,
  usage: () => [...developerKeys.all, "usage"] as const,
  webhooks: () => [...developerKeys.all, "webhooks"] as const,
  deliveries: (endpointId: string) =>
    [...developerKeys.all, "deliveries", endpointId] as const,
};

// ─── Hooks ───────────────────────────────────────────────────────────────────

/** List OAuth API clients owned by the current user. */
export function useApiClients() {
  return useQuery<ApiClientListResponse>({
    queryKey: developerKeys.clients(),
    queryFn: () => api.get<ApiClientListResponse>("/api/v1/platform/clients"),
    staleTime: 60_000,
  });
}

/** Get API usage metrics for the current user's first client. */
export function useApiUsage(days = 30) {
  return useQuery<ApiUsageResponse>({
    queryKey: [...developerKeys.usage(), days],
    queryFn: () =>
      api.get<ApiUsageResponse>(`/api/v1/platform/usage?days=${days}`),
    staleTime: 60_000,
  });
}

/** List webhook endpoints for the current user's first client. */
export function useWebhooks() {
  return useQuery<WebhookEndpointListResponse>({
    queryKey: developerKeys.webhooks(),
    queryFn: () =>
      api.get<WebhookEndpointListResponse>("/api/v1/platform/webhooks"),
    staleTime: 30_000,
  });
}

/** Register a new webhook endpoint. */
export function useCreateWebhook() {
  const queryClient = useQueryClient();
  return useMutation<WebhookEndpoint, Error, CreateWebhookInput>({
    mutationFn: (data) =>
      api.post<WebhookEndpoint>("/api/v1/platform/webhooks", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: developerKeys.webhooks() });
    },
  });
}

/** Send a test ping event to a registered webhook endpoint. */
export function useSendTestEvent() {
  return useMutation<WebhookDeliveryResponse, Error, string>({
    mutationFn: (endpointId) =>
      api.post<WebhookDeliveryResponse>(
        `/api/v1/platform/webhooks/${endpointId}/test`
      ),
  });
}
