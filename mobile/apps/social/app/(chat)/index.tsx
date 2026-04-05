/**
 * Chat Conversations List Screen
 *
 * Shows list of chat conversations with last message preview,
 * unread count badges, and online presence indicators.
 * API: GET /api/v1/messages/conversations
 * Response: PaginatedResponse<Conversation>
 *
 * Messages require parent-approved contacts (under-13).
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import type { AgeTier } from '@bhapi/config';
import { Avatar, AgeTierGate } from '@bhapi/ui';
import { ApiClient } from '@bhapi/api';
import { tokenManager } from '@bhapi/auth';

const apiClient = new ApiClient({
  baseUrl: '',
  getToken: () => tokenManager.getToken(),
});

interface Conversation {
  id: string;
  type: string;
  title: string | null;
  created_by: string;
  member_count: number;
  created_at: string;
  participant_name: string;
  participant_avatar_url: string | null;
  last_message_preview: string | null;
  last_message_at: string | null;
  unread_count: number;
}

type ChatListState = 'loading' | 'loaded' | 'error' | 'refreshing';

// User's age tier — in production, sourced from auth context or profile
const DEFAULT_AGE_TIER: AgeTier = 'teen';
const PAGE_SIZE = 20;

/**
 * Format a timestamp into a relative time string for display.
 */
export function formatMessageTime(isoString: string | null): string {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'now';
  if (diffMins < 60) return `${diffMins}m`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d`;
  return date.toLocaleDateString();
}

export default function ChatListScreen() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [state, setState] = useState<ChatListState>('loading');
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  // In production, this comes from the user's profile/auth context
  const [ageTier] = useState<AgeTier>(DEFAULT_AGE_TIER);

  function loadConversations() {
    setState('loading');
    apiClient
      .get<{ items: Conversation[]; total: number }>(
        `/api/v1/messages/conversations?page=1&page_size=${PAGE_SIZE}`
      )
      .then((response) => {
        setConversations(response.items);
        setHasMore(response.items.length === PAGE_SIZE);
        setPage(1);
        setState('loaded');
      })
      .catch((e: any) => {
        setState('error');
        setError(e?.message ?? 'Could not load conversations.');
      });
  }

  useEffect(() => {
    loadConversations();
  }, []);

  function onRefresh() {
    setState('refreshing');
    loadConversations();
  }

  async function loadMore() {
    if (!hasMore || state === 'loading') return;
    const nextPage = page + 1;
    try {
      const response = await apiClient.get<{ items: Conversation[]; total: number }>(
        `/api/v1/messages/conversations?page=${nextPage}&page_size=${PAGE_SIZE}`
      );
      setConversations((prev) => [...prev, ...response.items]);
      setHasMore(response.items.length === PAGE_SIZE);
      setPage(nextPage);
    } catch {
      // Silently fail on load-more — user can scroll back
    }
  }

  function renderConversation({ item }: { item: Conversation }) {
    const displayName = item.title || item.participant_name || 'Chat';
    const isUnread = item.unread_count > 0;

    return React.createElement(
      TouchableOpacity,
      {
        style: styles.conversationRow,
        accessibilityLabel: `Chat with ${displayName}${isUnread ? `, ${item.unread_count} unread` : ''}`,
        // onPress: () => router.push({ pathname: '/(chat)/conversation', params: { id: item.id } }),
      },
      React.createElement(Avatar, {
        name: displayName,
        size: 'md',
      }),
      React.createElement(
        View,
        { style: styles.conversationInfo },
        React.createElement(
          View,
          { style: styles.conversationHeader },
          React.createElement(
            Text,
            { style: [styles.participantName, isUnread && styles.participantNameUnread] },
            displayName
          ),
          item.last_message_at
            ? React.createElement(
                Text,
                { style: [styles.messageTime, isUnread && styles.messageTimeUnread] },
                formatMessageTime(item.last_message_at)
              )
            : null
        ),
        React.createElement(
          View,
          { style: styles.messagePreviewRow },
          React.createElement(
            Text,
            {
              style: [styles.messagePreview, isUnread && styles.messagePreviewUnread],
              numberOfLines: 1,
            },
            item.last_message_preview ?? 'No messages yet'
          ),
          isUnread
            ? React.createElement(
                View,
                { style: styles.unreadBadge },
                React.createElement(
                  Text,
                  { style: styles.unreadCount },
                  item.unread_count > 99 ? '99+' : String(item.unread_count)
                )
              )
            : null
        )
      )
    );
  }

  if (state === 'loading' && conversations.length === 0) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading messages' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  if (state === 'error' && conversations.length === 0) {
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
        { onPress: loadConversations, style: styles.retryButton },
        React.createElement(Text, { style: styles.retryText }, 'Try again')
      )
    );
  }

  return React.createElement(
    View,
    { style: styles.container, accessibilityLabel: 'Messages' },
    React.createElement(
      Text,
      { style: styles.heading, accessibilityRole: 'header' },
      'Messages'
    ),
    // Entire messaging UI gated by can_message permission
    React.createElement(
      AgeTierGate,
      { permission: 'can_message', ageTier },
      React.createElement(FlatList, {
        data: conversations,
        keyExtractor: (item: Conversation) => item.id,
        renderItem: renderConversation,
        contentContainerStyle: styles.listContent,
        refreshControl: React.createElement(RefreshControl, {
          refreshing: state === 'refreshing',
          onRefresh,
          tintColor: colors.primary[600],
        }),
        onEndReached: loadMore,
        onEndReachedThreshold: 0.5,
        ListEmptyComponent: React.createElement(
          View,
          { style: styles.emptyContainer },
          React.createElement(
            Text,
            { style: styles.emptyTitle },
            'No messages yet'
          ),
          React.createElement(
            Text,
            { style: styles.emptyText },
            'Add friends to start chatting!'
          )
        ),
      })
    )
  );
}

// Exported for testing
export { type Conversation, type ChatListState, PAGE_SIZE, DEFAULT_AGE_TIER };

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
  heading: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    padding: spacing.md,
    fontFamily: typography.fontFamily,
  },
  listContent: {
    paddingHorizontal: spacing.md,
  },
  conversationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
    minHeight: 64,
  },
  conversationInfo: {
    flex: 1,
    marginLeft: spacing.md,
  },
  conversationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  participantName: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  participantNameUnread: {
    fontWeight: '700',
  },
  messageTime: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  messageTimeUnread: {
    color: colors.primary[600],
    fontWeight: '600',
  },
  messagePreviewRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.xs,
  },
  messagePreview: {
    flex: 1,
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  messagePreviewUnread: {
    color: colors.neutral[700],
    fontWeight: '500',
  },
  unreadBadge: {
    backgroundColor: colors.primary[600],
    borderRadius: 12,
    minWidth: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
    marginLeft: spacing.sm,
  },
  unreadCount: {
    color: '#FFFFFF',
    fontSize: typography.sizes.xs,
    fontWeight: '700',
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
