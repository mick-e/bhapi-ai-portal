"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface ThirdPartyConsentItem {
  id: string;
  group_id: string;
  member_id: string;
  parent_user_id: string;
  provider_key: string;
  provider_name: string;
  data_purpose: string;
  consented: boolean;
  consented_at: string | null;
  withdrawn_at: string | null;
  created_at: string;
}

export interface RetentionPolicy {
  id: string;
  group_id: string;
  data_type: string;
  retention_days: number;
  description: string;
  auto_delete: boolean;
  last_cleanup_at: string | null;
  records_deleted: number;
  created_at: string;
}

export interface RetentionDisclosure {
  group_id: string;
  generated_at: string;
  summary: string;
  policies: Array<{
    data_type: string;
    description: string;
    retention_days: number;
    auto_delete: boolean;
    records_deleted_to_date: number;
    next_scheduled_cleanup: string | null;
    minimum_allowed_days: number;
  }>;
}

export interface PushNotificationConsent {
  id: string;
  group_id: string;
  member_id: string;
  parent_user_id: string;
  notification_type: string;
  consented: boolean;
  consented_at: string | null;
  withdrawn_at: string | null;
  created_at: string;
}

export interface VideoVerification {
  id: string;
  group_id: string;
  parent_user_id: string;
  verification_method: string;
  status: string;
  yoti_session_id: string | null;
  verification_score: number | null;
  verified_at: string | null;
  expires_at: string | null;
  created_at: string;
}

// ─── Query keys ─────────────────────────────────────────────────────────────

export const coppaKeys = {
  all: ["coppa-privacy"] as const,
  thirdParty: (groupId: string, memberId: string) =>
    [...coppaKeys.all, "third-party", groupId, memberId] as const,
  retention: (groupId: string) =>
    [...coppaKeys.all, "retention", groupId] as const,
  retentionDisclosure: (groupId: string) =>
    [...coppaKeys.all, "retention-disclosure", groupId] as const,
  pushConsent: (groupId: string, memberId: string) =>
    [...coppaKeys.all, "push-consent", groupId, memberId] as const,
  videoVerifications: (groupId: string) =>
    [...coppaKeys.all, "video-verifications", groupId] as const,
  videoVerificationStatus: (groupId: string) =>
    [...coppaKeys.all, "video-status", groupId] as const,
};

// ─── Third-party consent ────────────────────────────────────────────────────

export function useThirdPartyConsents(groupId: string, memberId: string) {
  return useQuery<ThirdPartyConsentItem[]>({
    queryKey: coppaKeys.thirdParty(groupId, memberId),
    queryFn: () =>
      api.get(`/api/v1/compliance/coppa/third-party-consent?group_id=${groupId}&member_id=${memberId}`),
    enabled: !!groupId && !!memberId,
  });
}

export function useUpdateThirdPartyConsent(groupId: string, memberId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { provider_key: string; consented: boolean }) =>
      api.put<ThirdPartyConsentItem>(
        `/api/v1/compliance/coppa/third-party-consent?group_id=${groupId}&member_id=${memberId}`,
        data,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: coppaKeys.thirdParty(groupId, memberId) });
    },
  });
}

export function useRefusePartialCollection(groupId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { member_id: string; refuse_third_party_sharing: boolean }) =>
      api.post<ThirdPartyConsentItem[]>(
        `/api/v1/compliance/coppa/refuse-partial-collection?group_id=${groupId}`,
        data,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: coppaKeys.all });
    },
  });
}

// ─── Retention policies ─────────────────────────────────────────────────────

export function useRetentionPolicies(groupId: string) {
  return useQuery<RetentionPolicy[]>({
    queryKey: coppaKeys.retention(groupId),
    queryFn: () =>
      api.get(`/api/v1/compliance/coppa/retention?group_id=${groupId}`),
    enabled: !!groupId,
  });
}

export function useUpdateRetentionPolicy(groupId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { data_type: string; retention_days: number; auto_delete: boolean }) =>
      api.put<RetentionPolicy>(
        `/api/v1/compliance/coppa/retention?group_id=${groupId}`,
        data,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: coppaKeys.retention(groupId) });
    },
  });
}

export function useRetentionDisclosure(groupId: string) {
  return useQuery<RetentionDisclosure>({
    queryKey: coppaKeys.retentionDisclosure(groupId),
    queryFn: () =>
      api.get(`/api/v1/compliance/coppa/retention/disclosure?group_id=${groupId}`),
    enabled: !!groupId,
  });
}

// ─── Push notification consent ──────────────────────────────────────────────

export function usePushNotificationConsents(groupId: string, memberId: string) {
  return useQuery<PushNotificationConsent[]>({
    queryKey: coppaKeys.pushConsent(groupId, memberId),
    queryFn: () =>
      api.get(`/api/v1/compliance/coppa/push-consent?group_id=${groupId}&member_id=${memberId}`),
    enabled: !!groupId && !!memberId,
  });
}

export function useUpdatePushNotificationConsent(groupId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { member_id: string; notification_type: string; consented: boolean }) =>
      api.put<PushNotificationConsent>(
        `/api/v1/compliance/coppa/push-consent?group_id=${groupId}`,
        data,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: coppaKeys.all });
    },
  });
}

// ─── Video verification ─────────────────────────────────────────────────────

export function useVideoVerifications(groupId: string) {
  return useQuery<VideoVerification[]>({
    queryKey: coppaKeys.videoVerifications(groupId),
    queryFn: () =>
      api.get(`/api/v1/compliance/coppa/video-verifications?group_id=${groupId}`),
    enabled: !!groupId,
  });
}

export function useVideoVerificationStatus(groupId: string) {
  return useQuery<{ group_id: string; has_valid_verification: boolean }>({
    queryKey: coppaKeys.videoVerificationStatus(groupId),
    queryFn: () =>
      api.get(`/api/v1/compliance/coppa/video-verification-status?group_id=${groupId}`),
    enabled: !!groupId,
  });
}

export function useInitiateVideoVerification(groupId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { verification_method: string }) =>
      api.post<VideoVerification>(
        `/api/v1/compliance/coppa/video-verification?group_id=${groupId}`,
        data,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: coppaKeys.videoVerifications(groupId) });
      qc.invalidateQueries({ queryKey: coppaKeys.videoVerificationStatus(groupId) });
    },
  });
}
