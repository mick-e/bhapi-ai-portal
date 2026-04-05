/**
 * Profile Screen — Full profile view with avatar, display name, bio,
 * age tier badge, follower/following counts, post grid/list, edit button.
 *
 * API: GET /api/v1/social/profiles/me
 * API: GET /api/v1/social/posts?author_id=<id>
 * API: GET /api/v1/social/followers
 * API: GET /api/v1/social/following
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
  FlatList,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import type { AgeTier } from '@bhapi/config';
import { Avatar, Badge, AgeTierGate } from '@bhapi/ui';
import type { Profile, SocialPost, ProfileVisibility } from '@bhapi/types';
import { ApiClient } from '@bhapi/api';
import { tokenManager } from '@bhapi/auth';

const apiClient = new ApiClient({
  baseUrl: '',
  getToken: () => tokenManager.getToken(),
});

type ProfileState = 'loading' | 'loaded' | 'error';
type PostViewMode = 'grid' | 'list';

// User's age tier — in production, sourced from auth context or profile
const DEFAULT_AGE_TIER: AgeTier = 'teen';

// Exported constants for testing
export const POST_PAGE_SIZE = 20;
export const VISIBILITY_LABELS: Record<string, string> = {
  public: 'Public',
  friends_only: 'Friends Only',
  private: 'Private',
};

export default function ProfileScreen() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [state, setState] = useState<ProfileState>('loading');
  const [error, setError] = useState('');
  const [ageTier] = useState<AgeTier>(DEFAULT_AGE_TIER);
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [postViewMode, setPostViewMode] = useState<PostViewMode>('list');
  const [followerCount, setFollowerCount] = useState(0);
  const [followingCount, setFollowingCount] = useState(0);

  useEffect(() => {
    loadProfile();
  }, []);

  async function loadProfile() {
    try {
      setState('loading');
      const data = await apiClient.get<Profile>('/api/v1/social/profiles/me');
      setProfile(data);
      const postsData = await apiClient.get<{ items: SocialPost[] }>(
        `/api/v1/social/posts?author_id=${(data as any).user_id}`
      );
      setPosts(postsData.items);
      setFollowerCount((data as any).follower_count ?? 0);
      setFollowingCount((data as any).following_count ?? 0);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Could not load profile.');
    }
  }

  const togglePostView = useCallback(() => {
    setPostViewMode((prev) => (prev === 'grid' ? 'list' : 'grid'));
  }, []);

  if (state === 'loading') {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading profile' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  if (state === 'error') {
    return React.createElement(
      View,
      { style: styles.centered },
      React.createElement(
        Text,
        { style: styles.errorText, accessibilityRole: 'alert' },
        error
      ),
      React.createElement(
        TouchableOpacity,
        { onPress: loadProfile, style: styles.retryButton },
        React.createElement(Text, { style: styles.retryText }, 'Try again')
      )
    );
  }

  return React.createElement(
    ScrollView,
    {
      style: styles.container,
      contentContainerStyle: styles.content,
      accessibilityLabel: 'Profile',
    },

    // Avatar (with upload indicator)
    React.createElement(
      View,
      { style: styles.avatarContainer },
      React.createElement(Avatar, {
        name: profile?.display_name ?? '?',
        size: 'lg',
        ...(profile?.avatar_url ? { source: { uri: profile.avatar_url } } : {}),
      })
    ),

    // Name + verification
    React.createElement(
      View,
      { style: styles.nameRow },
      React.createElement(
        Text,
        { style: styles.displayName, accessibilityRole: 'header' },
        profile?.display_name ?? 'User'
      ),
      profile?.is_verified
        ? React.createElement(Badge, {
            text: 'Verified',
            variant: 'success',
            style: { marginLeft: spacing.sm },
          })
        : null
    ),

    // Age tier badge
    profile?.age_tier
      ? React.createElement(
          View,
          { style: styles.tierContainer },
          React.createElement(Badge, {
            text: `Age ${profile.age_tier}`,
            variant: 'info',
            accessibilityLabel: `Age tier: ${profile.age_tier}`,
          })
        )
      : null,

    // Visibility badge
    React.createElement(
      View,
      { style: styles.visibilityContainer },
      React.createElement(Badge, {
        text: VISIBILITY_LABELS[(profile as any)?.visibility ?? 'friends_only'] ?? 'Friends Only',
        variant: 'default',
        accessibilityLabel: 'Profile visibility',
      })
    ),

    // Bio
    profile?.bio
      ? React.createElement(
          Text,
          { style: styles.bio },
          profile.bio
        )
      : React.createElement(
          Text,
          { style: styles.bioEmpty },
          'No bio yet'
        ),

    // Follower / Following counts (tappable)
    React.createElement(
      View,
      { style: styles.countsRow },
      React.createElement(
        TouchableOpacity,
        {
          style: styles.countItem,
          accessibilityLabel: `${followerCount} followers`,
          accessibilityRole: 'button',
        },
        React.createElement(
          Text,
          { style: styles.countValue },
          String(followerCount)
        ),
        React.createElement(
          Text,
          { style: styles.countLabel },
          'Followers'
        )
      ),
      React.createElement(
        TouchableOpacity,
        {
          style: styles.countItem,
          accessibilityLabel: `${followingCount} following`,
          accessibilityRole: 'button',
        },
        React.createElement(
          Text,
          { style: styles.countValue },
          String(followingCount)
        ),
        React.createElement(
          Text,
          { style: styles.countLabel },
          'Following'
        )
      )
    ),

    // Edit Profile button (own profile only)
    React.createElement(
      TouchableOpacity,
      {
        style: styles.editProfileButton,
        accessibilityLabel: 'Edit Profile',
        accessibilityRole: 'button',
      },
      React.createElement(
        Text,
        { style: styles.editProfileText },
        'Edit Profile'
      )
    ),

    // Post view mode toggle
    React.createElement(
      View,
      { style: styles.postViewToggle },
      React.createElement(
        TouchableOpacity,
        {
          onPress: togglePostView,
          style: styles.toggleButton,
          accessibilityLabel: `Switch to ${postViewMode === 'grid' ? 'list' : 'grid'} view`,
          accessibilityRole: 'button',
        },
        React.createElement(
          Text,
          { style: styles.toggleText },
          postViewMode === 'grid' ? 'List View' : 'Grid View'
        )
      )
    ),

    // Post history section
    React.createElement(
      View,
      { style: styles.postsSection },
      React.createElement(
        Text,
        { style: styles.sectionTitle, accessibilityRole: 'header' },
        'Posts'
      ),
      posts.length === 0
        ? React.createElement(
            Text,
            { style: styles.emptyPosts },
            'No posts yet'
          )
        : posts.map((post) =>
            React.createElement(
              View,
              { key: post.id, style: postViewMode === 'grid' ? styles.postGrid : styles.postList },
              React.createElement(Text, { style: styles.postContent }, post.content),
              React.createElement(
                Text,
                { style: styles.postMeta },
                `${post.likes_count} likes · ${post.comments_count} comments`
              )
            )
          )
    ),

    // Member since
    React.createElement(
      Text,
      { style: styles.memberSince },
      `Member since ${profile?.created_at ?? '--'}`
    ),

    // Create group chat — gated by can_create_group_chat permission
    React.createElement(
      View,
      { style: styles.actionSection },
      React.createElement(
        AgeTierGate,
        { permission: 'can_create_group_chat', ageTier },
        React.createElement(
          TouchableOpacity,
          {
            style: styles.createGroupButton,
            accessibilityLabel: 'Create group chat',
            accessibilityRole: 'button',
          },
          React.createElement(
            Text,
            { style: styles.createGroupText },
            'Create Group Chat'
          )
        )
      )
    )
  );
}

// Exported for testing
export { type ProfileState, type PostViewMode };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  content: {
    alignItems: 'center',
    padding: spacing.lg,
    paddingTop: spacing.xl,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
  },
  avatarContainer: {
    marginBottom: spacing.md,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  displayName: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  tierContainer: {
    marginBottom: spacing.xs,
  },
  visibilityContainer: {
    marginBottom: spacing.md,
  },
  bio: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    textAlign: 'center',
    marginBottom: spacing.lg,
    lineHeight: 22,
    fontFamily: typography.fontFamily,
  },
  bioEmpty: {
    fontSize: typography.sizes.base,
    color: colors.neutral[400],
    textAlign: 'center',
    marginBottom: spacing.lg,
    fontStyle: 'italic',
    fontFamily: typography.fontFamily,
  },
  countsRow: {
    flexDirection: 'row',
    gap: spacing.xl,
    marginBottom: spacing.lg,
  },
  countItem: {
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  countValue: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  countLabel: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  editProfileButton: {
    borderColor: colors.primary[600],
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    marginBottom: spacing.lg,
    minHeight: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  editProfileText: {
    color: colors.primary[600],
    fontSize: typography.sizes.base,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  postViewToggle: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    width: '100%',
    marginBottom: spacing.sm,
  },
  toggleButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
  },
  toggleText: {
    color: colors.primary[700],
    fontSize: typography.sizes.sm,
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  postsSection: {
    width: '100%',
    marginBottom: spacing.lg,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[900],
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  emptyPosts: {
    fontSize: typography.sizes.base,
    color: colors.neutral[400],
    textAlign: 'center',
    paddingVertical: spacing.lg,
    fontFamily: typography.fontFamily,
  },
  postGrid: {
    padding: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  postList: {
    padding: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  postContent: {
    fontSize: typography.sizes.base,
    color: colors.neutral[800],
    fontFamily: typography.fontFamily,
  },
  postMeta: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    marginTop: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  memberSince: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.base,
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  retryButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  retryText: {
    color: colors.primary[700],
    fontSize: typography.sizes.base,
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  actionSection: {
    marginTop: spacing.lg,
    width: '100%',
  },
  createGroupButton: {
    backgroundColor: colors.primary[600],
    borderRadius: 8,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  createGroupText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
});
