"use client";

import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api-client";
import type { AcademicReport } from "@/types";

export const academicKeys = {
  all: ["academic"] as const,
  report: (groupId: string, memberId: string, startDate?: string, endDate?: string) =>
    [...academicKeys.all, "report", groupId, memberId, startDate, endDate] as const,
};

export function useAcademicReport(
  groupId: string | null,
  memberId: string | null,
  startDate?: string,
  endDate?: string,
) {
  return useQuery<AcademicReport>({
    queryKey: academicKeys.report(
      groupId || "",
      memberId || "",
      startDate,
      endDate,
    ),
    queryFn: () =>
      analyticsApi.academicReport(groupId!, memberId!, startDate, endDate),
    enabled: !!groupId && !!memberId,
  });
}
