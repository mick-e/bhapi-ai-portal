/**
 * ModerationNotice — Banner component showing moderation status to content authors.
 *
 * States:
 *   - pending: Yellow banner with clock icon — "Your post is being reviewed"
 *   - rejected: Red banner with reason + appeal button
 *   - removed: Gray banner — "Removed by moderator" with reason
 *   - approved: No banner (returns null)
 *
 * Uses age-appropriate language suitable for children 5-15.
 */
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

export type ModerationState = 'pending' | 'approved' | 'rejected' | 'removed' | 'escalated';

export interface ModerationNoticeProps {
  /** Current moderation status of the content. */
  status: ModerationState;
  /** Reason for rejection/removal (shown to user). */
  reason?: string;
  /** Whether the user has already appealed this decision. */
  hasAppealed?: boolean;
  /** Callback when the user taps the appeal button (rejected only). */
  onAppeal?: () => void;
  /** Custom style overrides. */
  style?: ViewStyle;
  /** Accessibility label override. */
  accessibilityLabel?: string;
}

// Age-appropriate messages for each state
const STATUS_MESSAGES: Record<string, string> = {
  pending: 'Your post is being reviewed by our safety team.',
  escalated: 'Your post is being reviewed by our safety team.',
  rejected: 'Your post was not approved.',
  removed: 'This post was removed by a moderator.',
};

const STATUS_ICONS: Record<string, string> = {
  pending: '\u{1F551}',    // Clock
  escalated: '\u{1F551}',  // Clock
  rejected: '\u{1F6AB}',   // No entry
  removed: '\u{26A0}',     // Warning
};

const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  pending: { bg: '#FEF3C7', text: '#92400E', border: '#FCD34D' },
  escalated: { bg: '#FEF3C7', text: '#92400E', border: '#FCD34D' },
  rejected: { bg: '#FEE2E2', text: '#991B1B', border: '#FCA5A5' },
  removed: { bg: '#F3F4F6', text: '#374151', border: '#D1D5DB' },
};

export function ModerationNotice({
  status,
  reason,
  hasAppealed = false,
  onAppeal,
  style,
  accessibilityLabel,
}: ModerationNoticeProps) {
  // Approved content does not need a notice
  if (status === 'approved') {
    return null;
  }

  const message = STATUS_MESSAGES[status] ?? STATUS_MESSAGES.pending;
  const icon = STATUS_ICONS[status] ?? STATUS_ICONS.pending;
  const colorScheme = STATUS_COLORS[status] ?? STATUS_COLORS.pending;

  const showAppealButton = status === 'rejected' && !hasAppealed && onAppeal;
  const showAppealedLabel = status === 'rejected' && hasAppealed;

  return React.createElement(
    View,
    {
      style: [
        styles.container,
        { backgroundColor: colorScheme.bg, borderColor: colorScheme.border },
        style,
      ],
      accessibilityRole: 'alert',
      accessibilityLabel: accessibilityLabel ?? message,
    },
    // Icon + message row
    React.createElement(
      View,
      { style: styles.headerRow },
      React.createElement(
        Text,
        { style: styles.icon },
        icon
      ),
      React.createElement(
        Text,
        { style: [styles.message, { color: colorScheme.text }] },
        message
      )
    ),
    // Reason (if provided)
    reason
      ? React.createElement(
          Text,
          {
            style: [styles.reason, { color: colorScheme.text }],
            accessibilityLabel: `Reason: ${reason}`,
          },
          `Reason: ${reason}`
        )
      : null,
    // Appeal button (rejected only, not yet appealed)
    showAppealButton
      ? React.createElement(
          TouchableOpacity,
          {
            style: styles.appealButton,
            onPress: onAppeal,
            accessibilityLabel: 'Appeal this decision',
            accessibilityRole: 'button',
          },
          React.createElement(
            Text,
            { style: styles.appealButtonText },
            'Appeal this decision'
          )
        )
      : null,
    // Appealed label
    showAppealedLabel
      ? React.createElement(
          Text,
          {
            style: [styles.appealedLabel, { color: colorScheme.text }],
            accessibilityLabel: 'Your appeal has been submitted',
          },
          'Your appeal has been submitted and is being reviewed.'
        )
      : null
  );
}

export const moderationNoticeStyles = {
  borderRadius: 8,
  padding: spacing.md,
};

const styles = StyleSheet.create({
  container: {
    borderRadius: 8,
    borderWidth: 1,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  icon: {
    fontSize: typography.sizes.lg,
    marginRight: spacing.sm,
  },
  message: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    flex: 1,
    fontFamily: typography.fontFamily,
  },
  reason: {
    fontSize: typography.sizes.sm,
    marginTop: spacing.xs,
    marginLeft: 28, // Align with text after icon
    fontFamily: typography.fontFamily,
  },
  appealButton: {
    marginTop: spacing.sm,
    marginLeft: 28,
    backgroundColor: colors.primary[600],
    borderRadius: 6,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.md,
    alignSelf: 'flex-start',
    minHeight: 44,
    justifyContent: 'center',
  },
  appealButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  appealedLabel: {
    fontSize: typography.sizes.sm,
    fontStyle: 'italic',
    marginTop: spacing.xs,
    marginLeft: 28,
    fontFamily: typography.fontFamily,
  },
});
