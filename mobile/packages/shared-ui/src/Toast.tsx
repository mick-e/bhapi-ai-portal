import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Animated, ViewStyle } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

export type ToastVariant = 'success' | 'error' | 'info' | 'warning';

export interface ToastProps {
  message: string;
  variant?: ToastVariant;
  visible: boolean;
  duration?: number;
  onDismiss?: () => void;
  style?: ViewStyle;
  accessibilityLabel?: string;
}

export const toastColors: Record<ToastVariant, { bg: string; text: string }> = {
  success: { bg: colors.semantic.success, text: '#FFFFFF' },
  error: { bg: colors.semantic.error, text: '#FFFFFF' },
  info: { bg: colors.semantic.info, text: '#FFFFFF' },
  warning: { bg: colors.semantic.warning, text: '#000000' },
};

export function Toast({
  message,
  variant = 'info',
  visible,
  duration = 3000,
  onDismiss,
  style,
  accessibilityLabel,
}: ToastProps) {
  const colorConfig = toastColors[variant];

  useEffect(() => {
    if (visible && duration > 0 && onDismiss) {
      const timer = setTimeout(onDismiss, duration);
      return () => clearTimeout(timer);
    }
  }, [visible, duration, onDismiss]);

  if (!visible) return null;

  return React.createElement(
    View,
    {
      style: [
        styles.toast,
        { backgroundColor: colorConfig.bg },
        style,
      ],
      accessibilityLabel: accessibilityLabel ?? message,
      accessibilityRole: 'alert',
    },
    React.createElement(
      Text,
      {
        style: [styles.text, { color: colorConfig.text }],
      },
      message
    )
  );
}

const styles = StyleSheet.create({
  toast: {
    position: 'absolute',
    top: spacing.xl,
    left: spacing.md,
    right: spacing.md,
    padding: spacing.md,
    borderRadius: 8,
    zIndex: 1000,
    elevation: 10,
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
  },
  text: {
    fontSize: typography.sizes.sm,
    fontWeight: '500',
    textAlign: 'center',
    fontFamily: typography.fontFamily,
  },
});

export function getToastAutoDismissMs(duration?: number): number {
  return duration ?? 3000;
}
