/**
 * Social feature types for the Bhapi Social (child) app.
 */

export interface Profile {
  id: string;
  user_id: string;
  display_name: string;
  avatar_url: string | null;
  bio: string | null;
  age_tier: AgeTier;
  is_verified: boolean;
  follower_count: number;
  following_count: number;
  created_at: string;
  updated_at: string;
}

export type AgeTier = '5-9' | '10-12' | '13-15';

export interface SocialPost {
  id: string;
  author_id: string;
  content: string;
  media_urls: string[];
  likes_count: number;
  comments_count: number;
  is_liked: boolean;
  moderation_status: ModerationStatus;
  visibility: PostVisibility;
  created_at: string;
  updated_at: string;
}

export type ModerationStatus = 'pending' | 'approved' | 'rejected' | 'flagged';
export type PostVisibility = 'public' | 'friends' | 'private';

export interface SocialComment {
  id: string;
  post_id: string;
  author_id: string;
  content: string;
  likes_count: number;
  is_liked: boolean;
  moderation_status: ModerationStatus;
  created_at: string;
}

export interface Follow {
  id: string;
  follower_id: string;
  following_id: string;
  status: FollowStatus;
  created_at: string;
}

export type FollowStatus = 'pending' | 'accepted' | 'blocked';

export interface ContactRequest {
  id: string;
  from_user_id: string;
  to_user_id: string;
  status: 'pending' | 'approved' | 'rejected';
  parent_approval_required: boolean;
  parent_approved: boolean | null;
  message: string | null;
  created_at: string;
}

export interface FeedItem {
  post: SocialPost;
  author: Pick<Profile, 'id' | 'display_name' | 'avatar_url' | 'is_verified'>;
}
