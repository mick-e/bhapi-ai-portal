/**
 * PostCard — Social feed post component.
 *
 * Displays author avatar, content, like/comment counts, moderation badge.
 * Used in the Social app feed screen.
 */
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

export interface PostCardAuthor {
  display_name: string;
  avatar_url: string | null;
  is_verified: boolean;
}

export interface PostCardProps {
  author: PostCardAuthor;
  content: string;
  likesCount: number;
  commentsCount: number;
  isLiked: boolean;
  moderationStatus: 'pending' | 'approved' | 'rejected' | 'flagged';
  createdAt: string;
  onPress?: () => void;
  onLikePress?: () => void;
  onCommentPress?: () => void;
  style?: ViewStyle;
  accessibilityLabel?: string;
}

const MODERATION_COLORS: Record<string, { bg: string; text: string }> = {
  pending: { bg: '#FEF3C7', text: '#92400E' },
  approved: { bg: '#DCFCE7', text: colors.semantic.success },
  rejected: { bg: '#FEE2E2', text: colors.semantic.error },
  flagged: { bg: '#FEE2E2', text: colors.semantic.error },
};

export function PostCard({
  author,
  content,
  likesCount,
  commentsCount,
  isLiked,
  moderationStatus,
  createdAt,
  onPress,
  onLikePress,
  onCommentPress,
  style,
  accessibilityLabel,
}: PostCardProps) {
  const initials = author.display_name
    .split(/\s+/)
    .map((w) => w.charAt(0))
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const modColor = MODERATION_COLORS[moderationStatus] ?? MODERATION_COLORS.pending;

  return React.createElement(
    TouchableOpacity,
    {
      style: [styles.card, style],
      onPress,
      disabled: !onPress,
      accessibilityLabel: accessibilityLabel ?? `Post by ${author.display_name}`,
    },
    // Author row
    React.createElement(
      View,
      { style: styles.authorRow },
      React.createElement(
        View,
        { style: styles.avatar },
        React.createElement(Text, { style: styles.avatarText }, initials)
      ),
      React.createElement(
        View,
        { style: styles.authorInfo },
        React.createElement(
          View,
          { style: styles.nameRow },
          React.createElement(
            Text,
            { style: styles.authorName },
            author.display_name
          ),
          author.is_verified
            ? React.createElement(Text, { style: styles.verifiedMark }, '\u2713')
            : null
        ),
        React.createElement(Text, { style: styles.timestamp }, createdAt)
      ),
      // Moderation badge (shown if not approved)
      moderationStatus !== 'approved'
        ? React.createElement(
            View,
            { style: [styles.modBadge, { backgroundColor: modColor.bg }] },
            React.createElement(
              Text,
              { style: [styles.modBadgeText, { color: modColor.text }] },
              moderationStatus
            )
          )
        : null
    ),
    // Content
    React.createElement(
      Text,
      { style: styles.content },
      content
    ),
    // Footer — likes and comments
    React.createElement(
      View,
      { style: styles.footer },
      React.createElement(
        TouchableOpacity,
        {
          style: styles.footerAction,
          onPress: onLikePress,
          disabled: !onLikePress,
          accessibilityLabel: `${likesCount} likes${isLiked ? ', liked' : ''}`,
        },
        React.createElement(
          Text,
          { style: [styles.actionText, isLiked ? styles.actionTextActive : null] },
          `${isLiked ? '\u2764' : '\u2661'} ${likesCount}`
        )
      ),
      React.createElement(
        TouchableOpacity,
        {
          style: styles.footerAction,
          onPress: onCommentPress,
          disabled: !onCommentPress,
          accessibilityLabel: `${commentsCount} comments`,
        },
        React.createElement(
          Text,
          { style: styles.actionText },
          `\u{1F4AC} ${commentsCount}`
        )
      )
    )
  );
}

export const postCardStyles = {
  borderRadius: 8,
  padding: spacing.md,
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    padding: spacing.md,
    marginBottom: spacing.md,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  authorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.primary[500],
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.sm,
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.sm,
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
  authorInfo: {
    flex: 1,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  authorName: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  verifiedMark: {
    color: colors.accent[500],
    fontSize: typography.sizes.sm,
    fontWeight: '700',
    marginLeft: spacing.xs,
  },
  timestamp: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  modBadge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: 8,
  },
  modBadgeText: {
    fontSize: typography.sizes.xs,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  content: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    lineHeight: 22,
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  footer: {
    flexDirection: 'row',
    gap: spacing.lg,
    borderTopWidth: 1,
    borderTopColor: colors.neutral[100],
    paddingTop: spacing.sm,
  },
  footerAction: {
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: 44,
  },
  actionText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  actionTextActive: {
    color: colors.semantic.error,
  },
});
