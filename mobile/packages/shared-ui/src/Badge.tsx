import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

export type BadgeVariant = 'info' | 'success' | 'warning' | 'error';

export interface BadgeProps {
  text: string;
  variant?: BadgeVariant;
  style?: ViewStyle;
  accessibilityLabel?: string;
}

export const badgeColors: Record<BadgeVariant, { bg: string; text: string }> = {
  info: { bg: '#DBEAFE', text: colors.semantic.info },
  success: { bg: '#DCFCE7', text: colors.semantic.success },
  warning: { bg: '#FEF3C7', text: '#92400E' },
  error: { bg: '#FEE2E2', text: colors.semantic.error },
};

export function Badge({
  text,
  variant = 'info',
  style,
  accessibilityLabel,
}: BadgeProps) {
  const colorConfig = badgeColors[variant];

  return React.createElement(
    View,
    {
      style: [
        styles.badge,
        { backgroundColor: colorConfig.bg },
        style,
      ],
      accessibilityLabel: accessibilityLabel ?? text,
    },
    React.createElement(
      Text,
      {
        style: [styles.text, { color: colorConfig.text }],
      },
      text
    )
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  text: {
    fontSize: typography.sizes.xs,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
});
