/**
 * Creative React Query hooks for the Bhapi Social (child) app.
 * API: /api/v1/creative/
 *
 * Provides hooks for:
 *   - AI art generation + listing
 *   - Story templates + creation + listing
 *   - Sticker packs
 *   - Post to feed
 *
 * All data fetching uses @tanstack/react-query.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ApiClient } from '@bhapi/api';
import type { AgeTier } from '@bhapi/config';

const apiClient = new ApiClient({ baseUrl: '' });

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

const KEYS = {
  art: (memberId: string) => ['creative', 'art', memberId] as const,
  storyTemplates: (ageTier?: AgeTier) => ['creative', 'story-templates', ageTier ?? 'all'] as const,
  stories: (memberId: string) => ['creative', 'stories', memberId] as const,
  stickerPacks: () => ['creative', 'sticker-packs'] as const,
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface GenerateArtPayload {
  prompt: string;
  member_id: string;
  style?: string;
}

export interface ArtResult {
  id: string;
  prompt: string;
  image_url: string | null;
  moderation_status: 'pending' | 'approved' | 'rejected';
  created_at: string;
}

export interface StoryTemplate {
  id: string;
  theme: string;
  title: string;
  preview: string;
  template_type: 'fill_in_blank' | 'guided_outline' | 'free_write';
  age_tiers: AgeTier[];
}

export interface CreateStoryPayload {
  member_id: string;
  template_id: string;
  content: string;
  title?: string;
}

export interface StoryResult {
  id: string;
  member_id: string;
  template_id: string;
  title: string;
  content: string;
  moderation_status: 'pending' | 'approved' | 'rejected';
  created_at: string;
}

export interface StickerPack {
  id: string;
  name: string;
  category: 'branded' | 'seasonal' | 'educational' | 'my_stickers';
  stickers: Array<{
    id: string;
    image_url: string;
    name: string;
    category: string;
  }>;
}

export interface PostToFeedPayload {
  member_id: string;
  content_type: 'art' | 'story' | 'drawing';
  content_id: string;
  caption?: string;
}

export interface PostResult {
  post_id: string;
  moderation_status: 'pending' | 'approved' | 'rejected';
}

// ---------------------------------------------------------------------------
// Art hooks
// ---------------------------------------------------------------------------

/** POST /api/v1/creative/art — generate AI art from a prompt. */
export function useGenerateArt() {
  const queryClient = useQueryClient();
  return useMutation<ArtResult, Error, GenerateArtPayload>({
    mutationFn: (payload) =>
      apiClient.post<ArtResult>('/api/v1/creative/art', payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['creative', 'art', data.member_id] });
    },
  });
}

/** GET /api/v1/creative/art?member_id=<id> — list a member's art creations. */
export function useMyArt(memberId: string) {
  return useQuery<ArtResult[]>({
    queryKey: KEYS.art(memberId),
    queryFn: () =>
      apiClient.get<ArtResult[]>(`/api/v1/creative/art?member_id=${memberId}`),
    enabled: Boolean(memberId),
  });
}

// ---------------------------------------------------------------------------
// Story hooks
// ---------------------------------------------------------------------------

/** GET /api/v1/creative/story-templates?age_tier=<tier> — list story templates. */
export function useStoryTemplates(ageTier?: AgeTier) {
  const query = ageTier ? `?age_tier=${ageTier}` : '';
  return useQuery<StoryTemplate[]>({
    queryKey: KEYS.storyTemplates(ageTier),
    queryFn: () =>
      apiClient.get<StoryTemplate[]>(`/api/v1/creative/story-templates${query}`),
  });
}

/** POST /api/v1/creative/stories — create a new story. */
export function useCreateStory() {
  const queryClient = useQueryClient();
  return useMutation<StoryResult, Error, CreateStoryPayload>({
    mutationFn: (payload) =>
      apiClient.post<StoryResult>('/api/v1/creative/stories', payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['creative', 'stories', data.member_id] });
    },
  });
}

/** GET /api/v1/creative/stories?member_id=<id> — list a member's stories. */
export function useMyStories(memberId: string) {
  return useQuery<StoryResult[]>({
    queryKey: KEYS.stories(memberId),
    queryFn: () =>
      apiClient.get<StoryResult[]>(`/api/v1/creative/stories?member_id=${memberId}`),
    enabled: Boolean(memberId),
  });
}

// ---------------------------------------------------------------------------
// Sticker hooks
// ---------------------------------------------------------------------------

/** GET /api/v1/creative/sticker-packs — list all curated sticker packs. */
export function useStickerPacks() {
  return useQuery<StickerPack[]>({
    queryKey: KEYS.stickerPacks(),
    queryFn: () =>
      apiClient.get<StickerPack[]>('/api/v1/creative/sticker-packs'),
    staleTime: 1000 * 60 * 30, // 30 minutes — packs change infrequently
  });
}

// ---------------------------------------------------------------------------
// Feed integration
// ---------------------------------------------------------------------------

/** POST /api/v1/social/posts — share a creative item to the social feed. */
export function usePostToFeed() {
  const queryClient = useQueryClient();
  return useMutation<PostResult, Error, PostToFeedPayload>({
    mutationFn: (payload) =>
      apiClient.post<PostResult>('/api/v1/social/posts', {
        content_type: payload.content_type,
        content_id: payload.content_id,
        caption: payload.caption,
        member_id: payload.member_id,
      }),
    onSuccess: () => {
      // Invalidate feed so new post appears
      queryClient.invalidateQueries({ queryKey: ['social', 'feed'] });
    },
  });
}
