/**
 * Chat Conversations List Screen
 *
 * Shows list of chat conversations with last message preview.
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
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import type { AgeTier } from '@bhapi/config';
import { Avatar, AgeTierGate } from '@bhapi/ui';

interface Conversation {
  id: string;
  participant_name: string;
  participant_avatar_url: string | null;
  last_message: string | null;
  last_message_at: string | null;
  unread_count: number;
}

type ChatListState = 'loading' | 'loaded' | 'error';

// User's age tier — in production, sourced from auth context or profile
const DEFAULT_AGE_TIER: AgeTier = 'teen';

export default function ChatListScreen() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [state, setState] = useState<ChatListState>('loading');
  const [error, setError] = useState('');
  // In production, this comes from the user's profile/auth context
  const [ageTier] = useState<AgeTier>(DEFAULT_AGE_TIER);

  useEffect(() => {
    loadConversations();
  }, []);

  async function loadConversations() {
    try {
      setState('loading');
      // API call: GET /api/v1/messages/conversations
      // const response = await apiClient.get<PaginatedResponse<Conversation>>('/api/v1/messages/conversations');
      // setConversations(response.items);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Could not load messages.');
    }
  }

  function renderConversation({ item }: { item: Conversation }) {
    return React.createElement(
      TouchableOpacity,
      {
        style: styles.conversationRow,
        accessibilityLabel: `Chat with ${item.participant_name}${item.unread_count > 0 ? `, ${item.unread_count} unread` : ''}`,
        // onPress: () => router.push({ pathname: '/(chat)/conversation', params: { id: item.id } }),
      },
      React.createElement(Avatar, {
        name: item.participant_name,
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
            { style: styles.participantName },
            item.participant_name
          ),
          item.last_message_at
            ? React.createElement(
                Text,
                { style: styles.messageTime },
                item.last_message_at
              )
            : null
        ),
        React.createElement(
          View,
          { style: styles.messagePreviewRow },
          React.createElement(
            Text,
            { style: styles.messagePreview, numberOfLines: 1 },
            item.last_message ?? 'No messages yet'
          ),
          item.unread_count > 0
            ? React.createElement(
                View,
                { style: styles.unreadBadge },
                React.createElement(
                  Text,
                  { style: styles.unreadCount },
                  String(item.unread_count)
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
export { type Conversation, type ChatListState };

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
  messageTime: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
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
