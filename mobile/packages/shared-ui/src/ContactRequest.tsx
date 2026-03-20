/**
 * ContactRequest — Contact/friend request card.
 *
 * Shows requester info with accept/reject buttons.
 * For under-13 users, parent approval is required (shown as badge).
 */
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

export interface ContactRequestProps {
  requesterName: string;
  requesterAvatarUrl: string | null;
  message: string | null;
  requiresParentApproval: boolean;
  onAccept: () => void;
  onReject: () => void;
  isProcessing?: boolean;
  style?: ViewStyle;
  accessibilityLabel?: string;
}

export function ContactRequest({
  requesterName,
  requesterAvatarUrl,
  message,
  requiresParentApproval,
  onAccept,
  onReject,
  isProcessing = false,
  style,
  accessibilityLabel,
}: ContactRequestProps) {
  const initials = requesterName
    .split(/\s+/)
    .map((w) => w.charAt(0))
    .join('')
    .toUpperCase()
    .slice(0, 2);

  return React.createElement(
    View,
    {
      style: [styles.card, style],
      accessibilityLabel:
        accessibilityLabel ?? `Friend request from ${requesterName}`,
    },
    // Requester info
    React.createElement(
      View,
      { style: styles.infoRow },
      React.createElement(
        View,
        { style: styles.avatar },
        React.createElement(Text, { style: styles.avatarText }, initials)
      ),
      React.createElement(
        View,
        { style: styles.nameContainer },
        React.createElement(
          Text,
          { style: styles.requesterName },
          requesterName
        ),
        requiresParentApproval
          ? React.createElement(
              View,
              { style: styles.parentBadge },
              React.createElement(
                Text,
                { style: styles.parentBadgeText },
                'Needs parent approval'
              )
            )
          : null
      )
    ),

    // Message
    message
      ? React.createElement(
          Text,
          { style: styles.message },
          `"${message}"`
        )
      : null,

    // Action buttons
    React.createElement(
      View,
      { style: styles.actions },
      React.createElement(
        TouchableOpacity,
        {
          style: styles.rejectButton,
          onPress: onReject,
          disabled: isProcessing,
          accessibilityLabel: `Reject request from ${requesterName}`,
          accessibilityRole: 'button',
        },
        React.createElement(
          Text,
          { style: styles.rejectText },
          'Decline'
        )
      ),
      React.createElement(
        TouchableOpacity,
        {
          style: [styles.acceptButton, isProcessing ? styles.buttonDisabled : null],
          onPress: onAccept,
          disabled: isProcessing,
          accessibilityLabel: `Accept request from ${requesterName}`,
          accessibilityRole: 'button',
        },
        React.createElement(
          Text,
          { style: styles.acceptText },
          requiresParentApproval ? 'Request Approval' : 'Accept'
        )
      )
    )
  );
}

export const contactRequestStyles = {
  borderRadius: 8,
  minButtonHeight: 44,
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    padding: spacing.md,
    marginBottom: spacing.sm,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 2,
    elevation: 2,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.accent[500],
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.md,
    minWidth: 44,
    minHeight: 44,
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
  nameContainer: {
    flex: 1,
  },
  requesterName: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  parentBadge: {
    backgroundColor: '#FEF3C7',
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: 8,
    alignSelf: 'flex-start',
    marginTop: spacing.xs,
  },
  parentBadgeText: {
    fontSize: typography.sizes.xs,
    color: '#92400E',
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  message: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontStyle: 'italic',
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'flex-end',
  },
  rejectButton: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    minHeight: 44,
    justifyContent: 'center',
  },
  rejectText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  acceptButton: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 8,
    backgroundColor: colors.primary[600],
    minHeight: 44,
    justifyContent: 'center',
  },
  acceptText: {
    fontSize: typography.sizes.sm,
    color: '#FFFFFF',
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
});
