"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface DataDashboardResponse {
  member_name: string;
  data_summary: {
    capture_events_count: number;
    platforms_monitored: string[];
    risk_events_count: number;
    high_severity_count: number;
    alerts_sent_count: number;
  };
  third_party_sharing: Array<{
    provider: string;
    consented: boolean;
    last_updated: string | null;
  }>;
  retention_policies: Array<{
    data_type: string;
    retention_days: number;
    auto_delete: boolean;
    estimated_deletion: string | null;
  }>;
  degraded_providers: string[];
}

// ─── Hook ───────────────────────────────────────────────────────────────────

export function useDataDashboard(groupId: string, memberId: string) {
  return useQuery<DataDashboardResponse>({
    queryKey: ["data-dashboard", groupId, memberId],
    queryFn: () =>
      api.get<DataDashboardResponse>(
        `/api/v1/compliance/coppa/data-dashboard?group_id=${groupId}&member_id=${memberId}`
      ),
    enabled: !!groupId && !!memberId,
  });
}
