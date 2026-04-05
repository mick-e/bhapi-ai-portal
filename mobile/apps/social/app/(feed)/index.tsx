/**
 * Social Feed Screen
 *
 * Shows posts with PostCard, pull-to-refresh, infinite scroll.
 * API: GET /api/v1/social/feed?page=<n>
 * Response: PaginatedResponse<FeedItem>
 *
 * Content is pre-moderated for under-13 users.
 * Uses FlashList for performant rendering.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  RefreshControl,
  ActivityIndicator,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import type { AgeTier } from '@bhapi/config';
import type { FeedItem, PagedResponse } from '@bhapi/types';
import { AgeTierGate, PostCard } from '@bhapi/ui';
import { ApiClient } from '@bhapi/api';
import { tokenManager } from '@bhapi/auth';

const apiClient = new ApiClient({
  baseUrl: '',
  getToken: () => tokenManager.getToken(),
});

type FeedState = 'loading' | 'loaded' | 'error';

const DEFAULT_AGE_TIER: AgeTier = 'teen';
const PAGE_SIZE = 20;

export default function FeedScreen() {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [state, setState] = useState<FeedState>('loading');
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [ageTier] = useState<AgeTier>(DEFAULT_AGE_TIER);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const isLoadingRef = useRef(false);

  useEffect(() => {
    loadFeed(1, true);
  }, []);

  async function loadFeed(pageNum: number = 1, reset: boolean = false) {
    if (isLoadingRef.current) return;
    isLoadingRef.current = true;

    try {
      if (reset) setState('loading');

      const response = await apiClient.get<PagedResponse<FeedItem>>(
        `/api/v1/social/feed?page=${pageNum}&page_size=${PAGE_SIZE}`
      );
      const newItems = response.items;
      const totalPages = Math.ceil(response.total / PAGE_SIZE);

      if (reset) {
        setItems(newItems);
      } else {
        setItems((prev) => [...prev, ...newItems]);
      }

      setPage(pageNum);
      setHasMore(pageNum < totalPages);
      setState('loaded');
    } catch (e: any) {
      if (reset) {
        setState('error');
        setError(e?.message ?? 'Could not load your feed.');
      }
    } finally {
      isLoadingRef.current = false;
    }
  }

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadFeed(1, true);
    setRefreshing(false);
  }, []);

  const handleLoadMore = useCallback(async () => {
    if (!hasMore || loadingMore || isLoadingRef.current) return;
    setLoadingMore(true);
    await loadFeed(page + 1, false);
    setLoadingMore(false);
  }, [hasMore, loadingMore, page]);

  function handlePostPress(postId: string) {
    // Navigate to post detail: router.push(`/post-detail?id=${postId}`)
  }

  function handleLikePress(postId: string) {
    // API: POST /api/v1/social/posts/{postId}/like
    setItems((prev) =>
      prev.map((item) =>
        item.post.id === postId
          ? {
              ...item,
              post: {
                ...item.post,
                is_liked: !item.post.is_liked,
                likes_count: item.post.is_liked
                  ? item.post.likes_count - 1
                  : item.post.likes_count + 1,
              },
            }
          : item
      )
    );
  }

  function handleCommentPress(postId: string) {
    // Navigate to post detail comment section
  }

  function renderFeedItem({ item }: { item: FeedItem }) {
    return React.createElement(PostCard, {
      author: {
        display_name: item.author.display_name,
        avatar_url: item.author.avatar_url,
        is_verified: item.author.is_verified,
      },
      content: item.post.content,
      likesCount: item.post.likes_count,
      commentsCount: item.post.comments_count,
      isLiked: item.post.is_liked,
      moderationStatus: item.post.moderation_status,
      createdAt: item.post.created_at,
      onPress: () => handlePostPress(item.post.id),
      onLikePress: () => handleLikePress(item.post.id),
      onCommentPress: () => handleCommentPress(item.post.id),
      accessibilityLabel: `Post by ${item.author.display_name}`,
    });
  }

  function renderLoadingSkeletons() {
    const skeletons = Array.from({ length: 3 }, (_, i) =>
      React.createElement(
        View,
        { key: `skeleton-${i}`, style: styles.skeletonCard },
        React.createElement(View, { style: styles.skeletonHeader }),
        React.createElement(View, { style: styles.skeletonLine }),
        React.createElement(View, { style: styles.skeletonLineShort })
      )
    );
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading feed' },
      ...skeletons
    );
  }

  function renderFooter() {
    if (!loadingMore) return null;
    return React.createElement(
      View,
      { style: styles.footerLoader },
      React.createElement(ActivityIndicator, {
        size: 'small',
        color: colors.primary[600],
      })
    );
  }

  if (state === 'loading' && items.length === 0) {
    return renderLoadingSkeletons();
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
        { onPress: () => loadFeed(1, true), style: styles.retryButton },
        React.createElement(Text, { style: styles.retryText }, 'Try again')
      )
    );
  }

  // FlashList import would be: import { FlashList } from '@shopify/flash-list';
  // For now, using FlatList shape that can be swapped to FlashList.
  // FlashList requires estimatedItemSize and has the same API as FlatList.
  const { FlatList } = require('react-native');

  return React.createElement(
    View,
    { style: styles.container, accessibilityLabel: 'Feed' },
    // Create post FAB
    React.createElement(
      TouchableOpacity,
      {
        style: styles.createPostButton,
        accessibilityLabel: 'Create post',
        accessibilityRole: 'button',
        // onPress: () => router.push('/create-post'),
      },
      React.createElement(
        Text,
        { style: styles.createPostText },
        '+ New Post'
      )
    ),
    // Video upload button — gated by can_upload_video permission
    React.createElement(
      AgeTierGate,
      { permission: 'can_upload_video', ageTier },
      React.createElement(
        TouchableOpacity,
        {
          style: styles.videoUploadButton,
          accessibilityLabel: 'Upload video',
          accessibilityRole: 'button',
        },
        React.createElement(
          Text,
          { style: styles.videoUploadText },
          'Upload Video'
        )
      )
    ),
    React.createElement(FlatList, {
      data: items,
      keyExtractor: (item: FeedItem) => item.post.id,
      renderItem: renderFeedItem,
      estimatedItemSize: 200,
      refreshControl: React.createElement(RefreshControl, {
        refreshing,
        onRefresh: handleRefresh,
        tintColor: colors.primary[600],
      }),
      onEndReached: handleLoadMore,
      onEndReachedThreshold: 0.5,
      ListFooterComponent: renderFooter,
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
export { type FeedState, PAGE_SIZE, DEFAULT_AGE_TIER };

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
    padding: spacing.md,
  },
  listContent: {
    padding: spacing.md,
  },
  createPostButton: {
    backgroundColor: colors.primary[600],
    borderRadius: 8,
    padding: spacing.md,
    marginHorizontal: spacing.md,
    marginTop: spacing.md,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  createPostText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  videoUploadButton: {
    backgroundColor: colors.accent[500],
    borderRadius: 8,
    padding: spacing.md,
    marginHorizontal: spacing.md,
    marginTop: spacing.sm,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  videoUploadText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '600',
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
  footerLoader: {
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  skeletonCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    padding: spacing.md,
    marginBottom: spacing.md,
    width: '90%',
  },
  skeletonHeader: {
    width: 120,
    height: 16,
    backgroundColor: colors.neutral[200],
    borderRadius: 4,
    marginBottom: spacing.sm,
  },
  skeletonLine: {
    width: '100%',
    height: 12,
    backgroundColor: colors.neutral[100],
    borderRadius: 4,
    marginBottom: spacing.xs,
  },
  skeletonLineShort: {
    width: '60%',
    height: 12,
    backgroundColor: colors.neutral[100],
    borderRadius: 4,
  },
});
