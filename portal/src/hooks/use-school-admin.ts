"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface SchoolDevice {
  id: string;
  device_id: string;
  device_name: string;
  os: string;
  status: "active" | "inactive" | "pending" | "error";
  last_sync: string | null;
  assigned_to: string | null;
  extension_version: string | null;
  created_at: string;
}

export interface DeploymentStatus {
  total_devices: number;
  active_devices: number;
  pending_devices: number;
  inactive_devices: number;
  error_devices: number;
  last_updated: string;
  extension_coverage_percent: number;
}

export interface SchoolPolicy {
  id: string;
  name: string;
  description: string;
  policy_type: "acceptable_use" | "data_handling" | "model_access" | "cost_control";
  enforcement_level: "warn" | "block" | "audit";
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DeviceFilters {
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedDevices {
  items: SchoolDevice[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ─── Query Keys ─────────────────────────────────────────────────────────────

export const schoolAdminKeys = {
  all: ["school-admin"] as const,
  devices: (schoolId: string, filters?: DeviceFilters) =>
    [...schoolAdminKeys.all, "devices", schoolId, filters] as const,
  deployment: (schoolId: string) =>
    [...schoolAdminKeys.all, "deployment", schoolId] as const,
  policies: (schoolId: string) =>
    [...schoolAdminKeys.all, "policies", schoolId] as const,
};

// ─── Helper ─────────────────────────────────────────────────────────────────

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== ""
  );
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");
}

// ─── Hooks ──────────────────────────────────────────────────────────────────

export function useSchoolDevices(schoolId: string | null, filters?: DeviceFilters) {
  return useQuery<PaginatedDevices>({
    queryKey: schoolAdminKeys.devices(schoolId || "", filters),
    queryFn: () =>
      api.get<PaginatedDevices>(
        `/api/v1/integrations/google-admin/schools/${schoolId}/devices${qs({
          status: filters?.status,
          search: filters?.search,
          page: filters?.page,
          page_size: filters?.page_size,
        })}`
      ),
    enabled: !!schoolId,
  });
}

export function useDeploymentStatus(schoolId: string | null) {
  return useQuery<DeploymentStatus>({
    queryKey: schoolAdminKeys.deployment(schoolId || ""),
    queryFn: () =>
      api.get<DeploymentStatus>(
        `/api/v1/integrations/google-admin/schools/${schoolId}/status`
      ),
    enabled: !!schoolId,
    refetchInterval: 30_000,
  });
}

export function useSchoolPolicies(schoolId: string | null) {
  return useQuery<SchoolPolicy[]>({
    queryKey: schoolAdminKeys.policies(schoolId || ""),
    queryFn: () =>
      api.get<SchoolPolicy[]>(
        `/api/v1/governance/policies${qs({ school_id: schoolId || "" })}`
      ),
    enabled: !!schoolId,
  });
}

export function useAddDevice(schoolId: string) {
  const queryClient = useQueryClient();

  return useMutation<
    SchoolDevice,
    Error,
    { device_name: string; os: string; assigned_to?: string }
  >({
    mutationFn: (data) =>
      api.post<SchoolDevice>(
        `/api/v1/integrations/google-admin/schools/${schoolId}/devices`,
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: schoolAdminKeys.devices(schoolId),
      });
      queryClient.invalidateQueries({
        queryKey: schoolAdminKeys.deployment(schoolId),
      });
    },
  });
}

export function usePushPolicy(schoolId: string) {
  const queryClient = useQueryClient();

  return useMutation<
    SchoolPolicy,
    Error,
    { name: string; description: string; policy_type: string; enforcement_level: string }
  >({
    mutationFn: (data) =>
      api.post<SchoolPolicy>(
        `/api/v1/integrations/google-admin/schools/${schoolId}/policy`,
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: schoolAdminKeys.policies(schoolId),
      });
    },
  });
}

export function useUpdatePolicy(schoolId: string) {
  const queryClient = useQueryClient();

  return useMutation<
    SchoolPolicy,
    Error,
    { policyId: string; data: Partial<SchoolPolicy> }
  >({
    mutationFn: ({ policyId, data }) =>
      api.patch<SchoolPolicy>(
        `/api/v1/governance/policies/${policyId}`,
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: schoolAdminKeys.policies(schoolId),
      });
    },
  });
}

export function useDeletePolicy(schoolId: string) {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (policyId) =>
      api.delete<void>(`/api/v1/governance/policies/${policyId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: schoolAdminKeys.policies(schoolId),
      });
    },
  });
}
