"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { settingsApi } from "@/lib/api-client";
import type {
  GroupSettings,
  UpdateGroupSettingsRequest,
  UpdateProfileRequest,
  User,
} from "@/types";

export const settingsKeys = {
  all: ["settings"] as const,
  group: () => [...settingsKeys.all, "group"] as const,
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
