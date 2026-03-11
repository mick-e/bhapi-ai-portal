"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { privacyApi } from "@/lib/api-client";
import { useAuth } from "@/hooks/use-auth";
import type {
  MemberVisibility,
  ChildSelfView,
  ChildDashboard,
  SetVisibilityRequest,
  SetChildSelfViewRequest,
} from "@/types";

export const privacyKeys = {
  all: ["privacy"] as const,
  visibility: (groupId: string, memberId: string) =>
    [...privacyKeys.all, "visibility", groupId, memberId] as const,
  selfView: (groupId: string, memberId: string) =>
    [...privacyKeys.all, "self-view", groupId, memberId] as const,
  childDashboard: (memberId: string) =>
    [...privacyKeys.all, "child-dashboard", memberId] as const,
};

export function useVisibility(memberId: string) {
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useQuery<MemberVisibility>({
    queryKey: privacyKeys.visibility(groupId, memberId),
    queryFn: () => privacyApi.getVisibility(groupId, memberId),
    enabled: !!groupId && !!memberId,
  });
}

export function useSetVisibility() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useMutation({
    mutationFn: ({
      memberId,
      data,
    }: {
      memberId: string;
      data: SetVisibilityRequest;
    }) => privacyApi.setVisibility(groupId, memberId, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: privacyKeys.visibility(groupId, variables.memberId),
      });
    },
  });
}

export function useSelfView(memberId: string) {
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useQuery<ChildSelfView>({
    queryKey: privacyKeys.selfView(groupId, memberId),
    queryFn: () => privacyApi.getSelfView(groupId, memberId),
    enabled: !!groupId && !!memberId,
  });
}

export function useSetSelfView() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  return useMutation({
    mutationFn: ({
      memberId,
      data,
    }: {
      memberId: string;
      data: SetChildSelfViewRequest;
    }) => privacyApi.setSelfView(groupId, memberId, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: privacyKeys.selfView(groupId, variables.memberId),
      });
    },
  });
}

export function useChildDashboard(memberId: string) {
  return useQuery<ChildDashboard>({
    queryKey: privacyKeys.childDashboard(memberId),
    queryFn: () => privacyApi.getChildDashboard(memberId),
    enabled: !!memberId,
    refetchInterval: 60_000,
  });
}
