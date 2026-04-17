"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface FerpaRecord {
  id: string;
  record_type: string;
  description: string;
  designated_by: string;
  created_at: string;
  updated_at: string;
}

export interface FerpaAccessLogEntry {
  id: string;
  member_id: string;
  accessed_by: string;
  record_type: string;
  purpose: string;
  timestamp: string;
}

export interface FerpaSharingAgreement {
  id: string;
  partner_name: string;
  purpose: string;
  record_types: string[];
  status: string;
  expires_at: string | null;
  created_at: string;
}

export interface FerpaNotification {
  id: string;
  sent_at: string;
  recipients_count: number;
  academic_year: string;
  status: string;
}

// ─── Query Keys ─────────────────────────────────────────────────────────────

export const ferpaKeys = {
  all: ["ferpa"] as const,
  records: () => [...ferpaKeys.all, "records"] as const,
  accessLog: (memberId?: string) =>
    [...ferpaKeys.all, "access-log", memberId ?? "all"] as const,
  agreements: () => [...ferpaKeys.all, "agreements"] as const,
  notifications: () => [...ferpaKeys.all, "notifications"] as const,
};

// ─── Queries ────────────────────────────────────────────────────────────────

export function useFerpaRecords() {
  return useQuery<FerpaRecord[]>({
    queryKey: ferpaKeys.records(),
    queryFn: () => apiFetch<FerpaRecord[]>("/api/v1/ferpa/records"),
  });
}

export function useFerpaAccessLog(memberId?: string) {
  const path = memberId
    ? `/api/v1/ferpa/access-log?member_id=${encodeURIComponent(memberId)}`
    : "/api/v1/ferpa/access-log";
  return useQuery<FerpaAccessLogEntry[]>({
    queryKey: ferpaKeys.accessLog(memberId),
    queryFn: () => apiFetch<FerpaAccessLogEntry[]>(path),
  });
}

export function useFerpaSharingAgreements() {
  return useQuery<FerpaSharingAgreement[]>({
    queryKey: ferpaKeys.agreements(),
    queryFn: () =>
      apiFetch<FerpaSharingAgreement[]>("/api/v1/ferpa/sharing-agreements"),
  });
}

// ─── Mutations ──────────────────────────────────────────────────────────────

export function useDesignateRecord() {
  const queryClient = useQueryClient();

  return useMutation<
    FerpaRecord,
    Error,
    { record_type: string; description: string }
  >({
    mutationFn: (data) =>
      apiFetch<FerpaRecord>("/api/v1/ferpa/records", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ferpaKeys.records() });
    },
  });
}

export function useLogAccess() {
  const queryClient = useQueryClient();

  return useMutation<
    FerpaAccessLogEntry,
    Error,
    { member_id: string; record_type: string; purpose: string }
  >({
    mutationFn: (data) =>
      apiFetch<FerpaAccessLogEntry>("/api/v1/ferpa/access-log", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ferpaKeys.all });
    },
  });
}

export function useSendAnnualNotification() {
  const queryClient = useQueryClient();

  return useMutation<FerpaNotification, Error, { academic_year: string }>({
    mutationFn: (data) =>
      apiFetch<FerpaNotification>("/api/v1/ferpa/annual-notification", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ferpaKeys.notifications() });
    },
  });
}
