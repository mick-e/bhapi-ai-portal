"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { COPPAComplianceReport, COPPAReviewResponse } from "@/types";

export const coppaKeys = {
  all: ["coppa"] as const,
  checklist: (groupId: string) => [...coppaKeys.all, "checklist", groupId] as const,
};

export function useCOPPAChecklist(groupId: string | undefined) {
  return useQuery<COPPAComplianceReport>({
    queryKey: coppaKeys.checklist(groupId ?? ""),
    queryFn: () =>
      apiFetch<COPPAComplianceReport>(
        `/api/v1/compliance/coppa/checklist?group_id=${groupId}`
      ),
    enabled: !!groupId,
  });
}

export function useCOPPAExport(groupId: string | undefined) {
  return useMutation({
    mutationFn: async () => {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("bhapi_auth_token")
          : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const response = await fetch(
        `/api/v1/compliance/coppa/export?group_id=${groupId}`,
        { headers, credentials: "include" }
      );
      if (!response.ok) throw new Error("Failed to export evidence");
      return response.blob();
    },
  });
}

export function useCOPPAReview(groupId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation<COPPAReviewResponse>({
    mutationFn: () =>
      apiFetch<COPPAReviewResponse>(
        `/api/v1/compliance/coppa/review?group_id=${groupId}`,
        { method: "POST" }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: coppaKeys.all });
    },
  });
}
