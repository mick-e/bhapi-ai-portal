"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { settingsApi, apiKeysApi } from "@/lib/api-client";
import type {
  ApiKeyItem,
  CreateApiKeyRequest,
  CreateApiKeyResponse,
  GroupSettings,
  UpdateGroupSettingsRequest,
  UpdateProfileRequest,
  User,
} from "@/types";

export const settingsKeys = {
  all: ["settings"] as const,
  group: () => [...settingsKeys.all, "group"] as const,
  apiKeys: () => [...settingsKeys.all, "api-keys"] as const,
};

export function useGroupSettings() {
  return useQuery<GroupSettings>({
    queryKey: settingsKeys.group(),
    queryFn: () => settingsApi.getGroupSettings(),
  });
}

export function useUpdateGroupSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateGroupSettingsRequest) =>
      settingsApi.updateGroupSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.group() });
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateProfileRequest) =>
      settingsApi.updateProfile(data),
    onSuccess: (updatedUser: User) => {
      // Update the stored user in local storage
      if (typeof window !== "undefined") {
        localStorage.setItem("bhapi_user", JSON.stringify(updatedUser));
      }
      queryClient.invalidateQueries({ queryKey: settingsKeys.all });
    },
  });
}

// ─── API Keys ────────────────────────────────────────────────────────────────

export function useApiKeys() {
  return useQuery<ApiKeyItem[]>({
    queryKey: settingsKeys.apiKeys(),
    queryFn: () => apiKeysApi.list(),
  });
}

export function useGenerateApiKey() {
  const queryClient = useQueryClient();

  return useMutation<CreateApiKeyResponse, Error, CreateApiKeyRequest>({
    mutationFn: (data) => apiKeysApi.generate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.apiKeys() });
    },
  });
}

export function useRevokeApiKey() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (keyId) => apiKeysApi.revoke(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.apiKeys() });
    },
  });
}
