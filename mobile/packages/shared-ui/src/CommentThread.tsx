/**
 * CommentThread — List of comments with author + timestamp.
 *
 * Used in post detail views in the Social app.
 */
import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

export interface CommentItem {
  id: string;
  authorName: string;
  content: string;
  createdAt: string;
  isAuthor: boolean;
}

export interface CommentThreadProps {
  comments: CommentItem[];
  style?: ViewStyle;
  accessibilityLabel?: string;
}

export function CommentThread({
  comments,
  style,
  accessibilityLabel,
}: CommentThreadProps) {
  if (comments.length === 0) {
    return React.createElement(
      View,
      { style: [styles.container, style], accessibilityLabel: 'No comments' },
      React.createElement(
        Text,
        { style: styles.emptyText },
        'No comments yet. Be the first!'
      )
    );
  }

  return React.createElement(
    View,
    {
      style: [styles.container, style],
      accessibilityLabel: accessibilityLabel ?? `${comments.length} comments`,
    },
    ...comments.map((comment) =>
      React.createElement(
        View,
        { key: comment.id, style: styles.commentItem },
        React.createElement(
          View,
          { style: styles.commentHeader },
          React.createElement(
            View,
            { style: styles.authorDot },
            React.createElement(
              Text,
              { style: styles.authorDotText },
              comment.authorName.charAt(0).toUpperCase()
            )
          ),
          React.createElement(
            Text,
            { style: [styles.authorName, comment.isAuthor ? styles.authorNameHighlight : null] },
            comment.authorName
          ),
          React.createElement(
            Text,
            { style: styles.timestamp },
            comment.createdAt
          )
        ),
        React.createElement(
          Text,
          { style: styles.commentContent },
          comment.content
        )
      )
    )
  );
}

export const commentThreadStyles = {
  itemSpacing: spacing.sm,
};

const styles = StyleSheet.create({
  container: {
    // container
  },
  commentItem: {
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
  },
  commentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  authorDot: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.accent[500],
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.sm,
  },
  authorDotText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.xs,
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
  authorName: {
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    color: colors.neutral[900],
    flex: 1,
    fontFamily: typography.fontFamily,
  },
  authorNameHighlight: {
    color: colors.primary[700],
  },
  timestamp: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  commentContent: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    lineHeight: 20,
    paddingLeft: 36, // aligned with text after avatar
    fontFamily: typography.fontFamily,
  },
  emptyText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    textAlign: 'center',
    paddingVertical: spacing.lg,
    fontFamily: typography.fontFamily,
  },
});
