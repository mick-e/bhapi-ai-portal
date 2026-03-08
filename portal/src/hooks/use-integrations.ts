"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { integrationsApi } from "@/lib/api-client";
import type { SISConnection } from "@/types";

export const integrationsKeys = {
  all: ["integrations"] as const,
  connections: (groupId: string) =>
    [...integrationsKeys.all, "connections", groupId] as const,
};

export function useConnections(groupId: string | null) {
  return useQuery<SISConnection[]>({
    queryKey: integrationsKeys.connections(groupId || ""),
    queryFn: () => integrationsApi.listConnections(groupId!),
    enabled: !!groupId,
  });
}

export function useConnectSIS() {
  const queryClient = useQueryClient();

  return useMutation<
    SISConnection,
    Error,
    { group_id: string; provider: string; access_token: string }
  >({
    mutationFn: (data) => integrationsApi.connect(data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: integrationsKeys.connections(variables.group_id),
      });
    },
  });
}

export function useSyncConnection() {
  const queryClient = useQueryClient();

  return useMutation<
    { members_created: number; members_updated: number },
    Error,
    { connectionId: string; groupId: string }
  >({
    mutationFn: ({ connectionId }) => integrationsApi.sync(connectionId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: integrationsKeys.connections(variables.groupId),
      });
    },
  });
}

export function useDisconnectSIS() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { connectionId: string; groupId: string }>({
    mutationFn: ({ connectionId }) => integrationsApi.disconnect(connectionId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: integrationsKeys.connections(variables.groupId),
      });
    },
  });
}
