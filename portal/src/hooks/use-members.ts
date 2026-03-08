"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { membersApi } from "@/lib/api-client";
import { useAuth } from "@/hooks/use-auth";
import type {
  GroupMember,
  PaginatedResponse,
  InviteMemberRequest,
  UpdateMemberRequest,
  RecordConsentRequest,
} from "@/types";

export const memberKeys = {
  all: ["members"] as const,
  lists: () => [...memberKeys.all, "list"] as const,
  list: (groupId: string, params?: Record<string, unknown>) =>
    [...memberKeys.lists(), groupId, params] as const,
  detail: (groupId: string, memberId: string) =>
    [...memberKeys.all, "detail", groupId, memberId] as const,
};

export function useMembers(params?: {
  page?: number;
  page_size?: number;
  search?: string;
}) {
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useQuery<PaginatedResponse<GroupMember>>({
    queryKey: memberKeys.list(groupId, params),
    queryFn: () => membersApi.list(groupId, params),
    enabled: !!groupId,
  });
}

export function useMember(memberId: string) {
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useQuery<GroupMember>({
    queryKey: memberKeys.detail(groupId, memberId),
    queryFn: () => membersApi.get(groupId, memberId),
    enabled: !!groupId && !!memberId,
  });
}

export function useInviteMember() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useMutation({
    mutationFn: (data: InviteMemberRequest) =>
      membersApi.invite(groupId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memberKeys.lists() });
    },
  });
}

export function useUpdateMember() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useMutation({
    mutationFn: ({
      memberId,
      data,
    }: {
      memberId: string;
      data: UpdateMemberRequest;
    }) => membersApi.update(groupId, memberId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memberKeys.lists() });
    },
  });
}

export function useRemoveMember() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useMutation({
    mutationFn: (memberId: string) => membersApi.remove(groupId, memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memberKeys.lists() });
    },
  });
}

export function useRecordConsent() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useMutation({
    mutationFn: ({
      memberId,
      data,
    }: {
      memberId: string;
      data: RecordConsentRequest;
    }) => membersApi.recordConsent(groupId, memberId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memberKeys.lists() });
    },
  });
}

export function useBulkUpdateMembers() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useMutation({
    mutationFn: async ({
      memberIds,
      data,
    }: {
      memberIds: string[];
      data: UpdateMemberRequest;
    }) => {
      await Promise.all(
        memberIds.map((id) => membersApi.update(groupId, id, data))
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memberKeys.lists() });
    },
  });
}

export function useBulkRemoveMembers() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useMutation({
    mutationFn: async (memberIds: string[]) => {
      await Promise.all(
        memberIds.map((id) => membersApi.remove(groupId, id))
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: memberKeys.lists() });
    },
  });
}
