"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
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
      groupId ? api.get(`/api/v1/groups/${groupId}/emergency-contacts`) : [],
    enabled: !!groupId,
  });
}

export function useAddEmergencyContact() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id;

  return useMutation({
    mutationFn: (data: CreateEmergencyContactRequest) =>
      api.post<EmergencyContact>(`/api/v1/groups/${groupId}/emergency-contacts`, data),
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
      api.patch<EmergencyContact>(`/api/v1/groups/${groupId}/emergency-contacts/${id}`, data),
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
      api.delete(`/api/v1/groups/${groupId}/emergency-contacts/${contactId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: emergencyContactKeys.all });
    },
  });
}
