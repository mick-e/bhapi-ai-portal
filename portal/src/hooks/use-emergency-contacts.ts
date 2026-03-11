"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { emergencyContactsApi } from "@/lib/api-client";
import { useAuth } from "@/hooks/use-auth";

export interface EmergencyContact {
  id: string;
  group_id: string;
  name: string;
  relationship: string;
  phone: string | null;
  email: string | null;
  notify_on: string[];
  consent_given: boolean;
  consent_given_at: string | null;
  created_at: string | null;
}

export interface CreateEmergencyContactRequest {
  name: string;
  relationship: string;
  phone?: string;
  email?: string;
  notify_on?: string[];
  consent_given?: boolean;
}

export const emergencyContactKeys = {
  all: ["emergency-contacts"] as const,
  list: (groupId?: string) => [...emergencyContactKeys.all, "list", groupId] as const,
};

export function useEmergencyContacts() {
  const { user } = useAuth();
  const groupId = user?.group_id;

  return useQuery<EmergencyContact[]>({
    queryKey: emergencyContactKeys.list(groupId || undefined),
    queryFn: () =>
      groupId ? emergencyContactsApi.list(groupId) as Promise<EmergencyContact[]> : [],
    enabled: !!groupId,
  });
}

export function useAddEmergencyContact() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id;

  return useMutation({
    mutationFn: (data: CreateEmergencyContactRequest) =>
      emergencyContactsApi.add(groupId!, data) as Promise<EmergencyContact>,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: emergencyContactKeys.all });
    },
  });
}

export function useUpdateEmergencyContact() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id;

  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<CreateEmergencyContactRequest>) =>
      emergencyContactsApi.update(groupId!, id, data) as Promise<EmergencyContact>,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: emergencyContactKeys.all });
    },
  });
}

export function useRemoveEmergencyContact() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id;

  return useMutation({
    mutationFn: (contactId: string) =>
      emergencyContactsApi.remove(groupId!, contactId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: emergencyContactKeys.all });
    },
  });
}
