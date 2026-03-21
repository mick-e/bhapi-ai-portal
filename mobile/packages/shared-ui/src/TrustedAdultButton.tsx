/**
 * TrustedAdultButton — Subtle, accessible button for children to request a trusted adult.
 *
 * Design principles:
 *   - Subtle: Does not draw parent attention (no alarming colors/icons)
 *   - Accessible: Meets WCAG 2.1 AA, minimum 44px tap target
 *   - Child-friendly: Simple language, reassuring tone
 *   - Private: Clearly communicates this is confidential
 *
 * Usage:
 *   <TrustedAdultButton onPress={() => navigation.navigate('trusted-adult')} />
 */
import React from 'react';
import { TouchableOpacity, Text, View, StyleSheet, ViewStyle } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

export interface TrustedAdultButtonProps {
  /** Callback when the button is pressed. */
  onPress: () => void;
  /** Whether the button is disabled. */
  disabled?: boolean;
  /** Custom style overrides. */
  style?: ViewStyle;
  /** Accessibility label override. */
  accessibilityLabel?: string;
}

export function TrustedAdultButton({
  onPress,
  disabled = false,
  style,
  accessibilityLabel,
}: TrustedAdultButtonProps) {
  return React.createElement(
    TouchableOpacity,
    {
      onPress,
      disabled,
      style: [styles.container, disabled && styles.disabled, style],
      accessibilityRole: 'button',
      accessibilityLabel: accessibilityLabel ?? 'Talk to a trusted adult',
      accessibilityHint: 'Opens the trusted adult request screen. This is private.',
      activeOpacity: 0.7,
    },
    React.createElement(
      View,
      { style: styles.inner },
      React.createElement(
        Text,
        { style: styles.icon },
        '\u{1F64B}' // Raised hand emoji — friendly, not alarming
      ),
      React.createElement(
        View,
        { style: styles.textContainer },
        React.createElement(
          Text,
          { style: styles.title },
          'Need to talk to someone?'
        ),
        React.createElement(
          Text,
          { style: styles.subtitle },
          'This is private'
        )
      )
    )
  );
}

export const trustedAdultButtonStyles = {
  minHeight: 44,
  borderRadius: 12,
};

const styles = StyleSheet.create({
  container: {
    minHeight: 44,
    borderRadius: 12,
    backgroundColor: '#F9FAFB', // Very subtle gray background
    borderWidth: 1,
    borderColor: '#E5E7EB',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  disabled: {
    opacity: 0.5,
  },
  inner: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  icon: {
    fontSize: typography.sizes.xl,
    marginRight: spacing.sm,
  },
  textContainer: {
    flex: 1,
  },
  title: {
    fontSize: typography.sizes.base,
    fontWeight: '500',
    color: '#374151', // Neutral dark gray — not alarming
    fontFamily: typography.fontFamily,
  },
  subtitle: {
    fontSize: typography.sizes.xs,
    color: '#9CA3AF', // Light gray — subtle
    fontFamily: typography.fontFamily,
    marginTop: 2,
  },
});
