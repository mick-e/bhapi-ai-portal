"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface CreativeItem {
  id: string;
  member_id: string;
  member_name: string;
  content_type: "art" | "story" | "sticker" | "drawing";
  title: string;
  thumbnail_url: string | null;
  moderation_status: "pending" | "approved" | "rejected";
  created_at: string;
}

export interface CreativeReviewItem {
  id: string;
  member_id: string;
  member_name: string;
  content_type: string;
  title: string;
  thumbnail_url: string | null;
  moderation_status: "pending";
  flagged_reason: string | null;
  created_at: string;
}

// ─── Query Keys ─────────────────────────────────────────────────────────────

export const creativeKeys = {
  all: ["creative"] as const,
  gallery: () => [...creativeKeys.all, "gallery"] as const,
  reviewQueue: () => [...creativeKeys.all, "review-queue"] as const,
};

// ─── Queries ────────────────────────────────────────────────────────────────

export function useCreativeGallery() {
  return useQuery<CreativeItem[]>({
    queryKey: creativeKeys.gallery(),
    queryFn: () => apiFetch<CreativeItem[]>("/api/v1/creative/gallery"),
  });
}

export function useCreativeReviewQueue() {
  return useQuery<CreativeReviewItem[]>({
    queryKey: creativeKeys.reviewQueue(),
    queryFn: () => apiFetch<CreativeReviewItem[]>("/api/v1/creative/review"),
  });
}

// ─── Mutations ──────────────────────────────────────────────────────────────

export function useApproveCreative() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (itemId) =>
      apiFetch<void>(`/api/v1/creative/${itemId}/approve`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: creativeKeys.all });
    },
  });
}

export function useRejectCreative() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { itemId: string; reason?: string }>({
    mutationFn: ({ itemId, reason }) =>
      apiFetch<void>(`/api/v1/creative/${itemId}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: creativeKeys.all });
    },
  });
}
