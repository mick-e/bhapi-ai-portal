"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface SocialPost {
  id: string;
  author_id: string;
  author_name: string;
  content: string;
  media_count: number;
  has_image: boolean;
  has_video: boolean;
  moderation_status: "pending" | "approved" | "rejected";
  like_count: number;
  comment_count: number;
  created_at: string;
}

export interface SocialFeedResponse {
  items: SocialPost[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SocialContact {
  id: string;
  contact_id: string;
  contact_name: string;
  status: "approved" | "pending" | "blocked";
  requested_at: string;
  approved_at?: string;
}

export interface SocialContactsResponse {
  items: SocialContact[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SocialProfile {
  id: string;
  display_name: string;
  bio?: string;
  avatar_url?: string;
  follower_count: number;
  following_count: number;
  post_count: number;
  total_likes_received: number;
  total_comments_received: number;
  joined_at: string;
}

// ─── Query Keys ──────────────────────────────────────────────────────────────

export const socialMonitorKeys = {
  all: ["social-monitor"] as const,
  feed: (childId: string) =>
    [...socialMonitorKeys.all, "feed", childId] as const,
  contacts: (childId: string) =>
    [...socialMonitorKeys.all, "contacts", childId] as const,
  profile: (childId: string) =>
    [...socialMonitorKeys.all, "profile", childId] as const,
};

// ─── Hooks ───────────────────────────────────────────────────────────────────

export function useChildFeed(childId: string) {
  return useQuery<SocialFeedResponse>({
    queryKey: socialMonitorKeys.feed(childId),
    queryFn: () =>
      api.get<SocialFeedResponse>(
        `/api/v1/social/feed?member_id=${encodeURIComponent(childId)}`
      ),
    enabled: !!childId,
  });
}

export function useChildContacts(childId: string) {
  return useQuery<SocialContactsResponse>({
    queryKey: socialMonitorKeys.contacts(childId),
    queryFn: () =>
      api.get<SocialContactsResponse>(
        `/api/v1/contacts?member_id=${encodeURIComponent(childId)}`
      ),
    enabled: !!childId,
  });
}

export function useChildProfile(childId: string) {
  return useQuery<SocialProfile>({
    queryKey: socialMonitorKeys.profile(childId),
    queryFn: () =>
      api.get<SocialProfile>(`/api/v1/social/profiles/${encodeURIComponent(childId)}`),
    enabled: !!childId,
  });
}

export function useFlagPost() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ postId, reason }: { postId: string; reason: string }) =>
      api.post<{ success: boolean }>(`/api/v1/social/posts/${postId}/flag`, {
        reason,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: socialMonitorKeys.all });
    },
  });
}
