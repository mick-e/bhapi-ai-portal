"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useAuth } from "@/hooks/use-auth";
import type { FamilyAgreement, AgreementTemplate } from "@/types";

export const agreementKeys = {
  all: ["agreement"] as const,
  templates: () => [...agreementKeys.all, "templates"] as const,
  active: (groupId?: string) => [...agreementKeys.all, "active", groupId] as const,
};

export function useAgreementTemplates() {
  return useQuery<Record<string, AgreementTemplate>>({
    queryKey: agreementKeys.templates(),
    queryFn: () => api.get<Record<string, AgreementTemplate>>("/api/v1/groups/agreement-templates"),
  });
}

export function useActiveAgreement() {
  const { user } = useAuth();
  const groupId = user?.group_id;

  return useQuery<FamilyAgreement | null>({
    queryKey: agreementKeys.active(groupId || undefined),
    queryFn: () =>
      groupId ? api.get<FamilyAgreement>(`/api/v1/groups/${groupId}/agreement`) : null,
    enabled: !!groupId,
  });
}

export function useCreateAgreement() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id;

  return useMutation({
    mutationFn: (data: { template_id: string }) =>
      api.post<FamilyAgreement>(`/api/v1/groups/${groupId}/agreement`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agreementKeys.all });
    },
  });
}

export function useUpdateAgreement() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id;

  return useMutation({
    mutationFn: (data: { rules: { category: string; rule_text: string; enabled: boolean }[] }) =>
      api.patch<FamilyAgreement>(`/api/v1/groups/${groupId}/agreement`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agreementKeys.all });
    },
  });
}

export function useSignAgreement() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id;

  return useMutation({
    mutationFn: (data: { member_id: string; name: string }) =>
      api.post<FamilyAgreement>(`/api/v1/groups/${groupId}/agreement/sign`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agreementKeys.all });
    },
  });
}

export function useReviewAgreement() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id;

  return useMutation({
    mutationFn: () => api.post<FamilyAgreement>(`/api/v1/groups/${groupId}/agreement/review`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agreementKeys.all });
    },
  });
}
