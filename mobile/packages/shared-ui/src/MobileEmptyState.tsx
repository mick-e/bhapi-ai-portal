import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Button } from './Button';

interface MobileEmptyStateProps {
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function MobileEmptyState({ title, message, actionLabel, onAction }: MobileEmptyStateProps) {
  return React.createElement(
    View,
    { style: styles.container },
    React.createElement(Text, { style: styles.title }, title),
    React.createElement(Text, { style: styles.message }, message),
    actionLabel && onAction
      ? React.createElement(
          View,
          { style: styles.action },
          React.createElement(Button, {
            title: actionLabel,
            onPress: onAction,
            variant: 'primary',
            size: 'sm',
          })
        )
      : null
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  title: { fontSize: 18, fontWeight: '600', color: '#111827', textAlign: 'center' },
  message: { fontSize: 14, color: '#6B7280', textAlign: 'center', marginTop: 8 },
  action: { marginTop: 16 },
});
