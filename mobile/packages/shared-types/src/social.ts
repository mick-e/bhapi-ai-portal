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

// ---------------------------------------------------------------------------
// Onboarding
// ---------------------------------------------------------------------------

export type OnboardingStep = 'age_verify' | 'parent_consent' | 'profile_create' | 'complete';

export interface OnboardingState {
  step: OnboardingStep;
  age_verified: boolean;
  parent_consent_given: boolean;
  profile_created: boolean;
}

export interface YotiVerificationRequest {
  session_id: string;
  redirect_url: string;
}

export interface YotiVerificationResult {
  verified: boolean;
  age_estimate: number | null;
  session_id: string;
}

export interface ParentConsentRequest {
  child_user_id: string;
  parent_email: string;
  consent_type: 'social_access';
}

export interface ProfileCreateRequest {
  display_name: string;
  avatar_url?: string;
  bio?: string;
  date_of_birth: string;
}

// ---------------------------------------------------------------------------
// Post creation / detail
// ---------------------------------------------------------------------------

export interface CreatePostRequest {
  content: string;
  media_ids?: string[];
  visibility?: PostVisibility;
  hashtags?: string[];
}

export interface CreatePostResponse {
  id: string;
  moderation_status: ModerationStatus;
  message: string;
}

export interface PostDetailResponse extends SocialPost {
  author: Pick<Profile, 'id' | 'display_name' | 'avatar_url' | 'is_verified'>;
  comments: CommentResponse[];
  comment_count: number;
}

export interface CommentResponse {
  id: string;
  author_id: string;
  author_name: string;
  author_avatar: string | null;
  content: string;
  created_at: string;
}

export interface CreateCommentRequest {
  content: string;
}

// ---------------------------------------------------------------------------
// Hashtags
// ---------------------------------------------------------------------------

export interface Hashtag {
  id: string;
  name: string;
  post_count: number;
}
