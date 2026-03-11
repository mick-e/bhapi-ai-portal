"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { familyReportApi } from "@/lib/api-client";

export interface FamilyWeeklyReport {
  group_id: string;
  group_name: string;
  generated_at: string;
  period_start: string;
  period_end: string;
  family_safety_score: number;
  member_count: number;
  members: {
    member_id: string;
    display_name: string;
    role: string;
    safety_score: number;
    platforms_used: string[];
    risk_count: number;
    events_this_week: number;
    events_last_week: number;
    week_change: number;
  }[];
  highlights: {
    safest_member: string | null;
    most_improved: string | null;
  };
  action_items: {
    unresolved_alerts: number;
  };
}

export const familyReportKeys = {
  all: ["family-report"] as const,
  weekly: () => [...familyReportKeys.all, "weekly"] as const,
};

export function useFamilyWeeklyReport() {
  return useQuery<FamilyWeeklyReport>({
    queryKey: familyReportKeys.weekly(),
    queryFn: () => familyReportApi.getWeekly() as Promise<FamilyWeeklyReport>,
  });
}

export function useSendFamilyReport() {
  return useMutation({
    mutationFn: () => familyReportApi.send() as Promise<{ sent: boolean }>,
  });
}
