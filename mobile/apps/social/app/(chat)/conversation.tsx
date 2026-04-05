/**
 * Conversation Screen — Real-time chat with messages,
 * typing indicators, read receipts, and media support.
 *
 * API endpoints:
 *   GET  /api/v1/messages/conversations/:id/messages
 *   POST /api/v1/messages/conversations/:id/messages
 *   POST /api/v1/messages/conversations/:id/media
 *   PATCH /api/v1/messages/conversations/:id/read
 *   POST /api/v1/messages/conversations/:id/typing
 *   DELETE /api/v1/messages/conversations/:id/typing
 *   GET  /api/v1/messages/conversations/:id/typing
 *
 * WebSocket events: new_message, typing_start, typing_stop, read_receipt
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChatMessage {
  id: string;
  conversation_id: string;
  sender_id: string;
  content: string;
  message_type: string;
  moderation_status: string;
  created_at: string;
}

type ConversationState = 'loading' | 'loaded' | 'error' | 'sending';

// Character limits per age tier
export const MAX_MESSAGE_LENGTH: Record<string, number> = {
  young: 200,
  preteen: 500,
  teen: 1000,
};

export const TYPING_DEBOUNCE_MS = 1000;
export const TYPING_TIMEOUT_MS = 5000;
const PAGE_SIZE = 30;
const DEFAULT_AGE_TIER: AgeTier = 'teen';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  if (isToday) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

export function formatTypingIndicator(userNames: string[]): string {
  if (userNames.length === 0) return '';
  if (userNames.length === 1) return `${userNames[0]} is typing...`;
  if (userNames.length === 2) return `${userNames[0]} and ${userNames[1]} are typing...`;
  return `${userNames[0]} and ${userNames.length - 1} others are typing...`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ConversationScreen() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [state, setState] = useState<ConversationState>('loading');
  const [error, setError] = useState('');
  const [inputText, setInputText] = useState('');
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const [ageTier] = useState<AgeTier>(DEFAULT_AGE_TIER);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const typingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const flatListRef = useRef<FlatList>(null);
  const isTypingRef = useRef(false);

  // Conversation ID from route params (in production, via useLocalSearchParams)
  const conversationId = 'placeholder';

  useEffect(() => {
    loadMessages();
    markAsRead();

    // In production, set up WebSocket listeners:
    // ws.joinConversation(conversationId);
    // ws.on('new_message', handleNewMessage);
    // ws.on('typing_start', handleTypingStart);
    // ws.on('typing_stop', handleTypingStop);
    // ws.on('read_receipt', handleReadReceipt);
    // return () => {
    //   ws.leaveConversation(conversationId);
    //   ws.off('new_message', handleNewMessage);
    // };
  }, []);

  async function loadMessages() {
    try {
      setState('loading');
      const response = await apiClient.get<{ items: ChatMessage[]; total: number }>(
        `/api/v1/messages/conversations/${conversationId}/messages?page=1&page_size=${PAGE_SIZE}`
      );
      setMessages([...response.items].reverse());
      setHasMore(response.items.length === PAGE_SIZE);
      setPage(1);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Could not load messages.');
    }
  }

  async function loadOlderMessages() {
    if (!hasMore || state === 'loading') return;
    const nextPage = page + 1;
    try {
      const response = await apiClient.get<{ items: ChatMessage[]; total: number }>(
        `/api/v1/messages/conversations/${conversationId}/messages?page=${nextPage}&page_size=${PAGE_SIZE}`
      );
      setMessages((prev) => [...[...response.items].reverse(), ...prev]);
      setHasMore(response.items.length === PAGE_SIZE);
      setPage(nextPage);
    } catch {
      // Silently fail on load-older
    }
  }

  async function markAsRead() {
    // PATCH /api/v1/messages/conversations/{id}/read
    // await apiClient.patch(`/api/v1/messages/conversations/${conversationId}/read`);
    // ws.sendReadReceipt(conversationId);
  }

  const handleSend = useCallback(async () => {
    const trimmed = inputText.trim();
    if (!trimmed) return;

    const maxLen = MAX_MESSAGE_LENGTH[ageTier] || 1000;
    if (trimmed.length > maxLen) return;

    try {
      setState('sending');
      setInputText('');
      stopTypingIndicator();

      // Optimistic add
      const optimisticMessage: ChatMessage = {
        id: `temp-${Date.now()}`,
        conversation_id: conversationId,
        sender_id: 'me',
        content: trimmed,
        message_type: 'text',
        moderation_status: 'pending',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimisticMessage]);

      // POST /api/v1/messages/conversations/{id}/messages
      await apiClient.post(
        `/api/v1/messages/conversations/${conversationId}/messages`,
        { content: trimmed }
      );

      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError('Failed to send message.');
    }
  }, [inputText, ageTier, conversationId]);

  function handleTextChange(text: string) {
    setInputText(text);

    // Send typing indicator (debounced)
    if (!isTypingRef.current && text.length > 0) {
      isTypingRef.current = true;
      // POST /api/v1/messages/conversations/{id}/typing
      // ws.sendTypingStart(conversationId);
    }

    // Reset auto-stop timer
    if (typingTimerRef.current) {
      clearTimeout(typingTimerRef.current);
    }
    typingTimerRef.current = setTimeout(() => {
      stopTypingIndicator();
    }, TYPING_DEBOUNCE_MS);
  }

  function stopTypingIndicator() {
    if (isTypingRef.current) {
      isTypingRef.current = false;
      // DELETE /api/v1/messages/conversations/{id}/typing
      // ws.sendTypingStop(conversationId);
    }
    if (typingTimerRef.current) {
      clearTimeout(typingTimerRef.current);
      typingTimerRef.current = null;
    }
  }

  // WebSocket event handlers (used in production)
  // function handleNewMessage(data: any) {
  //   setMessages(prev => [...prev, data]);
  //   markAsRead();
  // }
  // function handleTypingStart(data: any) {
  //   setTypingUsers(prev => [...new Set([...prev, data.user_id])]);
  // }
  // function handleTypingStop(data: any) {
  //   setTypingUsers(prev => prev.filter(id => id !== data.user_id));
  // }

  function renderMessage({ item }: { item: ChatMessage }) {
    const isOwn = item.sender_id === 'me';
    const isPending = item.moderation_status === 'pending';
    const isMedia = item.message_type === 'image' || item.message_type === 'video';

    return React.createElement(
      View,
      {
        style: [
          styles.messageBubble,
          isOwn ? styles.ownMessage : styles.otherMessage,
        ],
        accessibilityLabel: `${isOwn ? 'You' : 'Contact'}: ${item.content}`,
      },
      isMedia
        ? React.createElement(
            View,
            { style: styles.mediaPlaceholder },
            React.createElement(
              Text,
              { style: styles.mediaPlaceholderText },
              `[${item.message_type}]`
            )
          )
        : null,
      React.createElement(
        Text,
        {
          style: [
            styles.messageText,
            isOwn ? styles.ownMessageText : styles.otherMessageText,
          ],
        },
        item.content
      ),
      React.createElement(
        View,
        { style: styles.messageFooter },
        React.createElement(
          Text,
          { style: styles.messageTimestamp },
          formatTimestamp(item.created_at)
        ),
        isPending
          ? React.createElement(
              Text,
              { style: styles.pendingIndicator },
              'Reviewing'
            )
          : null
      )
    );
  }

  if (state === 'loading' && messages.length === 0) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading conversation' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  if (state === 'error' && messages.length === 0) {
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
        { onPress: loadMessages, style: styles.retryButton },
        React.createElement(Text, { style: styles.retryText }, 'Try again')
      )
    );
  }

  const maxLen = MAX_MESSAGE_LENGTH[ageTier] || 1000;
  const charsLeft = maxLen - inputText.length;
  const isOverLimit = charsLeft < 0;

  return React.createElement(
    AgeTierGate,
    { permission: 'can_message', ageTier },
    React.createElement(
      KeyboardAvoidingView,
      {
        style: styles.container,
        behavior: Platform.OS === 'ios' ? 'padding' : undefined,
        keyboardVerticalOffset: 90,
      },
      // Message list
      React.createElement(FlatList, {
        ref: flatListRef,
        data: messages,
        keyExtractor: (item: ChatMessage) => item.id,
        renderItem: renderMessage,
        contentContainerStyle: styles.messageList,
        inverted: false,
        onEndReached: loadOlderMessages,
        onEndReachedThreshold: 0.3,
        ListEmptyComponent: React.createElement(
          View,
          { style: styles.emptyContainer },
          React.createElement(
            Text,
            { style: styles.emptyText },
            'Say hi to start the conversation!'
          )
        ),
      }),
      // Typing indicator
      typingUsers.length > 0
        ? React.createElement(
            View,
            { style: styles.typingContainer, accessibilityLabel: 'Someone is typing' },
            React.createElement(
              Text,
              { style: styles.typingText },
              formatTypingIndicator(typingUsers)
            )
          )
        : null,
      // Input bar
      React.createElement(
        View,
        { style: styles.inputContainer },
        React.createElement(TextInput, {
          style: [styles.textInput, isOverLimit && styles.textInputError],
          value: inputText,
          onChangeText: handleTextChange,
          placeholder: 'Type a message...',
          placeholderTextColor: colors.neutral[400],
          multiline: true,
          maxLength: maxLen + 50, // Allow slight over-type for UX
          accessibilityLabel: 'Message input',
        }),
        React.createElement(
          View,
          { style: styles.sendRow },
          React.createElement(
            Text,
            {
              style: [
                styles.charCount,
                isOverLimit && styles.charCountError,
              ],
            },
            `${charsLeft}`
          ),
          React.createElement(
            TouchableOpacity,
            {
              onPress: handleSend,
              disabled: inputText.trim().length === 0 || isOverLimit || state === 'sending',
              style: [
                styles.sendButton,
                (inputText.trim().length === 0 || isOverLimit) && styles.sendButtonDisabled,
              ],
              accessibilityLabel: 'Send message',
            },
            React.createElement(
              Text,
              { style: styles.sendButtonText },
              state === 'sending' ? '...' : 'Send'
            )
          )
        )
      )
    )
  );
}

// Exported for testing
export {
  type ChatMessage,
  type ConversationState,
  PAGE_SIZE as CONVERSATION_PAGE_SIZE,
};

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
  messageList: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  messageBubble: {
    maxWidth: '80%' as any,
    borderRadius: 16,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    marginVertical: spacing.xs,
  },
  ownMessage: {
    alignSelf: 'flex-end',
    backgroundColor: colors.primary[600],
    borderBottomRightRadius: 4,
  },
  otherMessage: {
    alignSelf: 'flex-start',
    backgroundColor: colors.neutral[200],
    borderBottomLeftRadius: 4,
  },
  messageText: {
    fontSize: typography.sizes.base,
    fontFamily: typography.fontFamily,
  },
  ownMessageText: {
    color: '#FFFFFF',
  },
  otherMessageText: {
    color: colors.neutral[900],
  },
  messageFooter: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
    marginTop: 2,
    gap: 4,
  },
  messageTimestamp: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
  },
  pendingIndicator: {
    fontSize: typography.sizes.xs,
    color: colors.semantic.warning,
    fontStyle: 'italic',
    fontFamily: typography.fontFamily,
  },
  mediaPlaceholder: {
    backgroundColor: colors.neutral[100],
    borderRadius: 8,
    height: 150,
    width: 200,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.xs,
  },
  mediaPlaceholderText: {
    color: colors.neutral[500],
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
  },
  typingContainer: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },
  typingText: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontStyle: 'italic',
    fontFamily: typography.fontFamily,
  },
  inputContainer: {
    borderTopWidth: 1,
    borderTopColor: colors.neutral[200],
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: '#FFFFFF',
  },
  textInput: {
    fontSize: typography.sizes.base,
    color: colors.neutral[900],
    maxHeight: 100,
    fontFamily: typography.fontFamily,
  },
  textInputError: {
    color: colors.semantic.error,
  },
  sendRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.xs,
  },
  charCount: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
  },
  charCountError: {
    color: colors.semantic.error,
    fontWeight: '600',
  },
  sendButton: {
    backgroundColor: colors.primary[600],
    borderRadius: 20,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    minHeight: 36,
    justifyContent: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: colors.neutral[300],
  },
  sendButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: spacing['2xl'],
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
