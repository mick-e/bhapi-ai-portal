/**
 * Social Feed Screen
 *
 * Shows posts with PostCard, pull-to-refresh.
 * API: GET /api/v1/social/feed?page=<n>
 * Response: PaginatedResponse<FeedItem>
 *
 * Content is pre-moderated for under-13 users.
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  RefreshControl,
  ActivityIndicator,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import type { FeedItem } from '@bhapi/types';

// PostCard will be imported from @bhapi/ui once registered in index.ts
// For now, inline rendering of feed items.

type FeedState = 'loading' | 'loaded' | 'error';

export default function FeedScreen() {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [state, setState] = useState<FeedState>('loading');
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadFeed();
  }, []);

  async function loadFeed() {
    try {
      setState('loading');
      // API call: GET /api/v1/social/feed
      // const response = await apiClient.get<PaginatedResponse<FeedItem>>('/api/v1/social/feed');
      // setItems(response.items);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Could not load your feed.');
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    await loadFeed();
    setRefreshing(false);
  }

  function renderFeedItem({ item }: { item: FeedItem }) {
    // Uses PostCard from @bhapi/ui
    return React.createElement(
      View,
      {
        style: styles.postCard,
        accessibilityLabel: `Post by ${item.author.display_name}`,
      },
      // Author header
      React.createElement(
        View,
        { style: styles.postHeader },
        React.createElement(
          View,
          { style: styles.authorAvatar },
          React.createElement(
            Text,
            { style: styles.authorInitial },
            item.author.display_name.charAt(0).toUpperCase()
          )
        ),
        React.createElement(
          View,
          { style: styles.authorInfo },
          React.createElement(
            Text,
            { style: styles.authorName },
            item.author.display_name
          ),
          item.author.is_verified
            ? React.createElement(
                Text,
                { style: styles.verifiedBadge },
                '\u2713'
              )
            : null
        )
      ),
      // Content
      React.createElement(
        Text,
        { style: styles.postContent },
        item.post.content
      ),
      // Engagement
      React.createElement(
        View,
        { style: styles.postFooter },
        React.createElement(
          Text,
          { style: styles.engagementText },
          `${item.post.likes_count} likes`
        ),
        React.createElement(
          Text,
          { style: styles.engagementText },
          `${item.post.comments_count} comments`
        )
      )
    );
  }

  if (state === 'loading' && items.length === 0) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading feed' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  if (state === 'error' && items.length === 0) {
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
        { onPress: loadFeed, style: styles.retryButton },
        React.createElement(Text, { style: styles.retryText }, 'Try again')
      )
    );
  }

  return React.createElement(
    View,
    { style: styles.container, accessibilityLabel: 'Feed' },
    React.createElement(FlatList, {
      data: items,
      keyExtractor: (item: FeedItem) => item.post.id,
      renderItem: renderFeedItem,
      refreshControl: React.createElement(RefreshControl, {
        refreshing,
        onRefresh: handleRefresh,
        tintColor: colors.primary[600],
      }),
      contentContainerStyle: styles.listContent,
      ListEmptyComponent: React.createElement(
        View,
        { style: styles.emptyContainer },
        React.createElement(
          Text,
          { style: styles.emptyTitle },
          'Nothing here yet!'
        ),
        React.createElement(
          Text,
          { style: styles.emptyText },
          'Follow some friends to see their posts.'
        )
      ),
    })
  );
}

// Exported for testing
export { type FeedState };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.neutral[50],
  },
  listContent: {
    padding: spacing.md,
  },
  postCard: {
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
  postHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  authorAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.primary[500],
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.sm,
  },
  authorInitial: {
    color: '#FFFFFF',
    fontSize: typography.sizes.lg,
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
  authorInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  authorName: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  verifiedBadge: {
    color: colors.accent[500],
    fontSize: typography.sizes.sm,
    marginLeft: spacing.xs,
    fontWeight: '700',
  },
  postContent: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    lineHeight: 22,
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  postFooter: {
    flexDirection: 'row',
    gap: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.neutral[100],
    paddingTop: spacing.sm,
  },
  engagementText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  emptyContainer: {
    paddingVertical: spacing['2xl'],
    alignItems: 'center',
  },
  emptyTitle: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.neutral[900],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  emptyText: {
    fontSize: typography.sizes.base,
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
