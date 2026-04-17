"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface RiskScore {
  member_id: string;
  member_name: string;
  overall_score: number;
  category_scores: Record<string, number>;
  trend: "improving" | "stable" | "worsening";
  updated_at: string;
}

export interface AnomalyAlert {
  id: string;
  member_id: string;
  member_name: string;
  anomaly_type: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
  detected_at: string;
  resolved: boolean;
}

export interface BehavioralBaseline {
  member_id: string;
  member_name: string;
  metric: string;
  baseline_value: number;
  current_value: number;
  deviation_percent: number;
  period: string;
}

export interface Correlation {
  id: string;
  rule_name: string;
  source_event: string;
  correlated_event: string;
  confidence: number;
  member_id: string;
  member_name: string;
  detected_at: string;
}

// ─── Query Keys ─────────────────────────────────────────────────────────────

export const insightsKeys = {
  all: ["insights"] as const,
  scores: () => [...insightsKeys.all, "scores"] as const,
  anomalies: () => [...insightsKeys.all, "anomalies"] as const,
  baselines: () => [...insightsKeys.all, "baselines"] as const,
  correlations: () => [...insightsKeys.all, "correlations"] as const,
};

// ─── Queries ────────────────────────────────────────────────────────────────

export function useRiskScores() {
  return useQuery<RiskScore[]>({
    queryKey: insightsKeys.scores(),
    queryFn: () => apiFetch<RiskScore[]>("/api/v1/intelligence/scores"),
  });
}

export function useAnomalyAlerts() {
  return useQuery<AnomalyAlert[]>({
    queryKey: insightsKeys.anomalies(),
    queryFn: () => apiFetch<AnomalyAlert[]>("/api/v1/intelligence/anomalies"),
  });
}

export function useBehavioralBaselines() {
  return useQuery<BehavioralBaseline[]>({
    queryKey: insightsKeys.baselines(),
    queryFn: () =>
      apiFetch<BehavioralBaseline[]>("/api/v1/intelligence/baselines"),
  });
}

export function useCorrelations() {
  return useQuery<Correlation[]>({
    queryKey: insightsKeys.correlations(),
    queryFn: () => apiFetch<Correlation[]>("/api/v1/intelligence/correlations"),
  });
}
