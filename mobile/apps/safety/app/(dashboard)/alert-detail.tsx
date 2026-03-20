/**
 * Alert Detail Screen
 *
 * Shows full alert details with actions: snooze, escalate, dismiss.
 * API: GET /api/v1/alerts/:id
 * Actions:
 *   POST /api/v1/alerts/:id/snooze { duration_hours }
 *   POST /api/v1/alerts/:id/escalate
 *   PATCH /api/v1/alerts/:id { status: 'dismissed' }
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Button, Badge, Card } from '@bhapi/ui';
import type { Alert, AlertSeverity } from '@bhapi/types';

type DetailState = 'loading' | 'loaded' | 'error';
type ActionState = 'idle' | 'processing' | 'done';

const SEVERITY_VARIANT: Record<AlertSeverity, 'info' | 'success' | 'warning' | 'error'> = {
  low: 'info',
  medium: 'warning',
  high: 'error',
  critical: 'error',
};

const SNOOZE_OPTIONS = [
  { hours: 1, label: '1 hour' },
  { hours: 4, label: '4 hours' },
  { hours: 24, label: '1 day' },
  { hours: 168, label: '1 week' },
];

export default function AlertDetailScreen() {
  const [state, setState] = useState<DetailState>('loading');
  const [alert, setAlert] = useState<Alert | null>(null);
  const [actionState, setActionState] = useState<ActionState>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [showSnoozeOptions, setShowSnoozeOptions] = useState(false);

  // In Expo Router, alert ID comes from route params:
  // const { id } = useLocalSearchParams<{ id: string }>();

  useEffect(() => {
    loadAlert();
  }, []);

  async function loadAlert() {
    try {
      setState('loading');
      // API call: GET /api/v1/alerts/:id
      // const data = await apiClient.get<Alert>(`/api/v1/alerts/${id}`);
      // setAlert(data);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setErrorMessage(e?.message ?? 'Failed to load alert details.');
    }
  }

  async function handleSnooze(hours: number) {
    try {
      setActionState('processing');
      // API call: POST /api/v1/alerts/:id/snooze
      // await apiClient.post(`/api/v1/alerts/${alert?.id}/snooze`, { duration_hours: hours });
      setShowSnoozeOptions(false);
      setActionState('done');
      // router.back();
    } catch (e: any) {
      setActionState('idle');
      setErrorMessage(e?.message ?? 'Failed to snooze alert.');
    }
  }

  async function handleEscalate() {
    try {
      setActionState('processing');
      // API call: POST /api/v1/alerts/:id/escalate
      // await apiClient.post(`/api/v1/alerts/${alert?.id}/escalate`, {});
      setActionState('done');
    } catch (e: any) {
      setActionState('idle');
      setErrorMessage(e?.message ?? 'Failed to escalate alert.');
    }
  }

  async function handleDismiss() {
    try {
      setActionState('processing');
      // API call: PATCH /api/v1/alerts/:id
      // await apiClient.put(`/api/v1/alerts/${alert?.id}`, { status: 'dismissed' });
      setActionState('done');
      // router.back();
    } catch (e: any) {
      setActionState('idle');
      setErrorMessage(e?.message ?? 'Failed to dismiss alert.');
    }
  }

  if (state === 'loading') {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading alert details' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  if (state === 'error' && !alert) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Alert detail error' },
      React.createElement(
        Text,
        { style: styles.errorText, accessibilityRole: 'alert' },
        errorMessage
      ),
      React.createElement(
        TouchableOpacity,
        { onPress: loadAlert, style: styles.retryButton },
        React.createElement(Text, { style: styles.retryText }, 'Tap to retry')
      )
    );
  }

  return React.createElement(
    ScrollView,
    {
      style: styles.container,
      contentContainerStyle: styles.content,
      accessibilityLabel: 'Alert detail',
    },
    // Header with severity badge
    React.createElement(
      View,
      { style: styles.header },
      React.createElement(Badge, {
        text: alert?.severity ?? 'unknown',
        variant: SEVERITY_VARIANT[alert?.severity ?? 'low'],
        style: styles.severityBadge,
      }),
      React.createElement(Badge, {
        text: alert?.status ?? 'unread',
        variant: 'info',
      })
    ),

    // Title
    React.createElement(
      Text,
      { style: styles.title, accessibilityRole: 'header' },
      alert?.title ?? 'Alert'
    ),

    // Description
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Alert description' },
      React.createElement(
        Text,
        { style: styles.description },
        alert?.description ?? ''
      )
    ),

    // Metadata
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Alert metadata' },
      React.createElement(
        Text,
        { style: styles.metaLabel },
        'Category'
      ),
      React.createElement(
        Text,
        { style: styles.metaValue },
        alert?.category?.replace(/_/g, ' ') ?? '--'
      ),
      alert?.platform
        ? React.createElement(
            View,
            null,
            React.createElement(Text, { style: styles.metaLabel }, 'Platform'),
            React.createElement(Text, { style: styles.metaValue }, alert.platform)
          )
        : null,
      React.createElement(Text, { style: styles.metaLabel }, 'Detected'),
      React.createElement(
        Text,
        { style: styles.metaValue },
        alert?.created_at ?? '--'
      )
    ),

    // Error message
    errorMessage
      ? React.createElement(
          Text,
          { style: styles.actionError, accessibilityRole: 'alert' },
          errorMessage
        )
      : null,

    // Snooze options panel
    showSnoozeOptions
      ? React.createElement(
          Card,
          { style: styles.card, accessibilityLabel: 'Snooze options' },
          React.createElement(
            Text,
            { style: styles.snoozeTitle },
            'Snooze for...'
          ),
          ...SNOOZE_OPTIONS.map((option) =>
            React.createElement(
              TouchableOpacity,
              {
                key: option.hours,
                style: styles.snoozeOption,
                onPress: () => handleSnooze(option.hours),
                accessibilityLabel: `Snooze for ${option.label}`,
              },
              React.createElement(
                Text,
                { style: styles.snoozeOptionText },
                option.label
              )
            )
          ),
          React.createElement(Button, {
            title: 'Cancel',
            onPress: () => setShowSnoozeOptions(false),
            variant: 'outline',
            size: 'sm',
            style: { marginTop: spacing.sm },
          })
        )
      : null,

    // Action buttons
    React.createElement(
      View,
      { style: styles.actions },
      React.createElement(Button, {
        title: 'Snooze',
        onPress: () => setShowSnoozeOptions(!showSnoozeOptions),
        variant: 'outline',
        disabled: actionState === 'processing',
        accessibilityLabel: 'Snooze this alert',
      }),
      React.createElement(Button, {
        title: 'Escalate',
        onPress: handleEscalate,
        variant: 'secondary',
        isLoading: actionState === 'processing',
        disabled: actionState === 'processing',
        accessibilityLabel: 'Escalate this alert',
      }),
      React.createElement(Button, {
        title: 'Dismiss',
        onPress: handleDismiss,
        variant: 'primary',
        disabled: actionState === 'processing',
        accessibilityLabel: 'Dismiss this alert',
      })
    )
  );
}

// Exported for testing
export { SNOOZE_OPTIONS, SEVERITY_VARIANT, type DetailState, type ActionState };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  content: {
    padding: spacing.md,
    paddingBottom: spacing['2xl'],
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.neutral[50],
  },
  header: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  severityBadge: {
    // extra styling if needed
  },
  title: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  card: {
    marginBottom: spacing.md,
  },
  description: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    lineHeight: 24,
    fontFamily: typography.fontFamily,
  },
  metaLabel: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontWeight: '600',
    textTransform: 'uppercase',
    marginTop: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  metaValue: {
    fontSize: typography.sizes.base,
    color: colors.neutral[900],
    marginTop: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  snoozeTitle: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  snoozeOption: {
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
    minHeight: 44,
    justifyContent: 'center',
  },
  snoozeOptionText: {
    fontSize: typography.sizes.base,
    color: colors.primary[700],
    fontFamily: typography.fontFamily,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  actionError: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    textAlign: 'center',
    marginBottom: spacing.md,
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
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    minHeight: 44,
    justifyContent: 'center',
  },
  retryText: {
    color: colors.primary[700],
    fontSize: typography.sizes.base,
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
});
