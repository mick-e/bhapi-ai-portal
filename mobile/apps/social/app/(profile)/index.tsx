/**
 * Profile Screen
 *
 * Shows user avatar, display name, bio, follower/following counts.
 * API: GET /api/v1/social/profile/me
 * Response: Profile
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Avatar, Badge } from '@bhapi/ui';
import type { Profile } from '@bhapi/types';

type ProfileState = 'loading' | 'loaded' | 'error';

export default function ProfileScreen() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [state, setState] = useState<ProfileState>('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    loadProfile();
  }, []);

  async function loadProfile() {
    try {
      setState('loading');
      // API call: GET /api/v1/social/profile/me
      // const data = await apiClient.get<Profile>('/api/v1/social/profile/me');
      // setProfile(data);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Could not load profile.');
    }
  }

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
    // Avatar
    React.createElement(
      View,
      { style: styles.avatarContainer },
      React.createElement(Avatar, {
        name: profile?.display_name ?? '?',
        size: 'lg',
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

    // Bio
    profile?.bio
      ? React.createElement(
          Text,
          { style: styles.bio },
          profile.bio
        )
      : null,

    // Follower counts
    React.createElement(
      View,
      { style: styles.countsRow },
      React.createElement(
        View,
        { style: styles.countItem, accessibilityLabel: `${profile?.follower_count ?? 0} followers` },
        React.createElement(
          Text,
          { style: styles.countValue },
          String(profile?.follower_count ?? 0)
        ),
        React.createElement(
          Text,
          { style: styles.countLabel },
          'Followers'
        )
      ),
      React.createElement(
        View,
        { style: styles.countItem, accessibilityLabel: `${profile?.following_count ?? 0} following` },
        React.createElement(
          Text,
          { style: styles.countValue },
          String(profile?.following_count ?? 0)
        ),
        React.createElement(
          Text,
          { style: styles.countLabel },
          'Following'
        )
      )
    ),

    // Member since
    React.createElement(
      Text,
      { style: styles.memberSince },
      `Member since ${profile?.created_at ?? '--'}`
    )
  );
}

// Exported for testing
export { type ProfileState };

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
  countsRow: {
    flexDirection: 'row',
    gap: spacing.xl,
    marginBottom: spacing.lg,
  },
  countItem: {
    alignItems: 'center',
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
});
