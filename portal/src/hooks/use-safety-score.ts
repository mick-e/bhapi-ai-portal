"use client";
import { useMemo } from "react";
import { useDashboardSummary } from "@/hooks/use-dashboard";

export interface SafetyScore {
  score: number;         // 0-100 (100 = safest)
  confidence: string;   // low | medium | high
  trend: string;        // increasing | stable | decreasing
  children_monitored: number;
  active_alerts: number;
}

/**
 * Derives a family safety score from the dashboard summary.
 * Score is computed as:
 *   100 - (critical_alerts * 20) - (high_risk_events * 10) - (unread_alerts * 2)
 * clamped to [0, 100].
 */
export function useSafetyScore() {
  const { data: dashboard, isLoading, isError, error } = useDashboardSummary();

  const data = useMemo<SafetyScore | undefined>(() => {
    if (!dashboard) return undefined;

    const criticalAlerts = dashboard.alert_summary.critical_count ?? 0;
    const unreadAlerts = dashboard.alert_summary.unread_count ?? 0;
    const highRiskEvents = dashboard.risk_summary.high_severity_count ?? 0;

    const rawScore =
      100 - criticalAlerts * 20 - highRiskEvents * 10 - unreadAlerts * 2;
    const score = Math.max(0, Math.min(100, rawScore));

    // Confidence: high when we have active members; low when no data
    const confidence =
      dashboard.active_members === 0
        ? "low"
        : dashboard.active_members >= 2
        ? "high"
        : "medium";

    return {
      score,
      confidence,
      trend: dashboard.risk_summary.trend ?? "stable",
      children_monitored: dashboard.active_members ?? 0,
      active_alerts: unreadAlerts,
    };
  }, [dashboard]);

  return { data, isLoading, isError, error };
}
