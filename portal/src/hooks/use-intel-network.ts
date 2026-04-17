"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface ThreatSignal {
  id: string;
  signal_type: string;
  severity: "low" | "medium" | "high" | "critical";
  pattern_data: Record<string, unknown>;
  sample_size: number;
  contributor_region: string | null;
  confidence: number;
  description: string | null;
  feedback_helpful: number;
  feedback_false_positive: number;
  created_at: string;
}

export interface NetworkSubscription {
  id: string;
  group_id: string;
  is_active: boolean;
  signal_types: string[];
  minimum_severity: string;
  created_at: string;
  updated_at: string;
}

export interface SubscribeRequest {
  signal_types?: string[];
  minimum_severity?: string;
}

export interface FeedbackRequest {
  signal_id: string;
  is_helpful: boolean;
  notes?: string;
}

// ─── Query Keys ─────────────────────────────────────────────────────────────

export const intelNetworkKeys = {
  all: ["intel-network"] as const,
  feed: () => [...intelNetworkKeys.all, "feed"] as const,
  subscription: () => [...intelNetworkKeys.all, "subscription"] as const,
};

// ─── Queries ────────────────────────────────────────────────────────────────

export function useIntelFeed() {
  return useQuery<ThreatSignal[]>({
    queryKey: intelNetworkKeys.feed(),
    queryFn: () => apiFetch<ThreatSignal[]>("/api/v1/intel-network/feed"),
    retry: false,
  });
}

export function useIntelSubscription() {
  return useQuery<NetworkSubscription>({
    queryKey: intelNetworkKeys.subscription(),
    queryFn: () =>
      apiFetch<NetworkSubscription>("/api/v1/intel-network/subscription"),
    retry: false,
  });
}

// ─── Mutations ──────────────────────────────────────────────────────────────

export function useSubscribeToNetwork() {
  const queryClient = useQueryClient();

  return useMutation<NetworkSubscription, Error, SubscribeRequest>({
    mutationFn: (data) =>
      apiFetch<NetworkSubscription>("/api/v1/intel-network/subscribe", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: intelNetworkKeys.all });
    },
  });
}

export function useUnsubscribeFromNetwork() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, void>({
    mutationFn: () =>
      apiFetch<void>("/api/v1/intel-network/subscribe", {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: intelNetworkKeys.all });
    },
  });
}

export function useSubmitSignalFeedback() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, FeedbackRequest>({
    mutationFn: (data) =>
      apiFetch<void>("/api/v1/intel-network/feedback", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: intelNetworkKeys.feed() });
    },
  });
}
