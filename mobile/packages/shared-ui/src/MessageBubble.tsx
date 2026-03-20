/**
 * MessageBubble — Chat message bubble.
 *
 * Sent messages: right-aligned, primary color background.
 * Received messages: left-aligned, neutral background.
 */
import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

export interface MessageBubbleProps {
  content: string;
  timestamp: string;
  isSent: boolean;
  senderName?: string;
  style?: ViewStyle;
  accessibilityLabel?: string;
}

export function MessageBubble({
  content,
  timestamp,
  isSent,
  senderName,
  style,
  accessibilityLabel,
}: MessageBubbleProps) {
  return React.createElement(
    View,
    {
      style: [
        styles.wrapper,
        isSent ? styles.wrapperSent : styles.wrapperReceived,
        style,
      ],
      accessibilityLabel:
        accessibilityLabel ??
        `${isSent ? 'You' : senderName ?? 'They'} said: ${content}`,
    },
    // Sender name for received messages
    !isSent && senderName
      ? React.createElement(
          Text,
          { style: styles.senderName },
          senderName
        )
      : null,
    // Bubble
    React.createElement(
      View,
      { style: [styles.bubble, isSent ? styles.bubbleSent : styles.bubbleReceived] },
      React.createElement(
        Text,
        { style: [styles.content, isSent ? styles.contentSent : styles.contentReceived] },
        content
      ),
      React.createElement(
        Text,
        { style: [styles.timestamp, isSent ? styles.timestampSent : styles.timestampReceived] },
        timestamp
      )
    )
  );
}

export const messageBubbleStyles = {
  sentBg: colors.primary[600],
  receivedBg: colors.neutral[100],
  maxWidth: '75%' as const,
};

const styles = StyleSheet.create({
  wrapper: {
    marginVertical: spacing.xs,
    paddingHorizontal: spacing.md,
  },
  wrapperSent: {
    alignItems: 'flex-end',
  },
  wrapperReceived: {
    alignItems: 'flex-start',
  },
  senderName: {
    fontSize: typography.sizes.xs,
    fontWeight: '600',
    color: colors.neutral[500],
    marginBottom: 2,
    marginLeft: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  bubble: {
    maxWidth: '75%',
    borderRadius: 16,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  bubbleSent: {
    backgroundColor: colors.primary[600],
    borderBottomRightRadius: 4,
  },
  bubbleReceived: {
    backgroundColor: colors.neutral[100],
    borderBottomLeftRadius: 4,
  },
  content: {
    fontSize: typography.sizes.base,
    lineHeight: 20,
    fontFamily: typography.fontFamily,
  },
  contentSent: {
    color: '#FFFFFF',
  },
  contentReceived: {
    color: colors.neutral[900],
  },
  timestamp: {
    fontSize: typography.sizes.xs,
    marginTop: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  timestampSent: {
    color: 'rgba(255,255,255,0.7)',
    textAlign: 'right',
  },
  timestampReceived: {
    color: colors.neutral[500],
  },
});
