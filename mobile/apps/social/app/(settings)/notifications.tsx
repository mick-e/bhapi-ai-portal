/**
 * Notification Preferences Screen
 *
 * Per-category toggles for push notifications:
 * messages, likes, comments, contact requests, moderation, weekly digest.
 *
 * API: GET /api/v1/social/profile/settings (notification prefs)
 * API: PUT /api/v1/social/profile/settings
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  Switch,
  ActivityIndicator,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Card } from '@bhapi/ui';

// ---------------------------------------------------------------------------
// Types & Constants
// ---------------------------------------------------------------------------

export interface NotificationPrefs {
  messages: boolean;
  likes: boolean;
  comments: boolean;
  contact_requests: boolean;
  moderation: boolean;
  weekly_digest: boolean;
}

export const DEFAULT_NOTIFICATION_PREFS: NotificationPrefs = {
  messages: true,
  likes: true,
  comments: true,
  contact_requests: true,
  moderation: true,
  weekly_digest: true,
};

export const NOTIFICATION_CATEGORIES: {
  key: keyof NotificationPrefs;
  label: string;
  description: string;
}[] = [
  {
    key: 'messages',
    label: 'Messages',
    description: 'New messages from friends',
  },
  {
    key: 'likes',
    label: 'Likes',
    description: 'When someone likes your post',
  },
  {
    key: 'comments',
    label: 'Comments',
    description: 'New comments on your posts',
  },
  {
    key: 'contact_requests',
    label: 'Contact Requests',
    description: 'New friend requests',
  },
  {
    key: 'moderation',
    label: 'Moderation',
    description: 'Content review updates',
  },
  {
    key: 'weekly_digest',
    label: 'Weekly Digest',
    description: 'Summary of your weekly activity',
  },
];

type ScreenState = 'loading' | 'idle' | 'saving' | 'error';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function NotificationPrefsScreen() {
  const [state, setState] = useState<ScreenState>('loading');
  const [prefs, setPrefs] = useState<NotificationPrefs>(DEFAULT_NOTIFICATION_PREFS);
  const [error, setError] = useState('');
  const [allEnabled, setAllEnabled] = useState(true);

  useEffect(() => {
    loadPrefs();
  }, []);

  // Compute master toggle from individual prefs
  useEffect(() => {
    const allOn = Object.values(prefs).every((v) => v === true);
    setAllEnabled(allOn);
  }, [prefs]);

  async function loadPrefs() {
    try {
      setState('loading');
      // API: GET /api/v1/social/profile/settings -> extract notification_prefs
      // const settings = await apiClient.get('/api/v1/social/profile/settings');
      // setPrefs(settings.notification_prefs ?? DEFAULT_NOTIFICATION_PREFS);
      setState('idle');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Could not load notification preferences.');
    }
  }

  const toggleCategory = useCallback(
    async (key: keyof NotificationPrefs) => {
      const updated = { ...prefs, [key]: !prefs[key] };
      setPrefs(updated);
      try {
        setState('saving');
        // API: PUT /api/v1/social/profile/settings
        // await apiClient.put('/api/v1/social/profile/settings', {
        //   notification_prefs: updated,
        // });
        setState('idle');
      } catch (e: any) {
        // Revert on failure
        setPrefs(prefs);
        setState('error');
        setError(e?.message ?? 'Could not save notification preference.');
      }
    },
    [prefs],
  );

  const toggleAll = useCallback(
    async (enable: boolean) => {
      const updated: NotificationPrefs = {
        messages: enable,
        likes: enable,
        comments: enable,
        contact_requests: enable,
        moderation: enable,
        weekly_digest: enable,
      };
      setPrefs(updated);
      try {
        setState('saving');
        // API: PUT /api/v1/social/profile/settings
        // await apiClient.put('/api/v1/social/profile/settings', {
        //   notification_prefs: updated,
        // });
        setState('idle');
      } catch (e: any) {
        setPrefs(prefs);
        setState('error');
        setError(e?.message ?? 'Could not update notifications.');
      }
    },
    [prefs],
  );

  if (state === 'loading') {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading notification preferences' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      }),
    );
  }

  return React.createElement(
    ScrollView,
    {
      style: styles.container,
      contentContainerStyle: styles.content,
      accessibilityLabel: 'Notification Preferences',
    },

    // Header
    React.createElement(
      Text,
      { style: styles.heading, accessibilityRole: 'header' },
      'Notifications',
    ),

    // Status
    state === 'saving'
      ? React.createElement(
          Text,
          { style: styles.savingText, accessibilityRole: 'alert' },
          'Saving...',
        )
      : null,

    state === 'error'
      ? React.createElement(
          Text,
          { style: styles.errorText, accessibilityRole: 'alert' },
          error,
        )
      : null,

    // Master toggle
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Master notification toggle' },
      React.createElement(
        View,
        { style: styles.toggleRow },
        React.createElement(
          View,
          { style: styles.toggleTextGroup },
          React.createElement(
            Text,
            { style: styles.masterLabel },
            'All Notifications',
          ),
          React.createElement(
            Text,
            { style: styles.toggleDesc },
            'Turn all notifications on or off',
          ),
        ),
        React.createElement(Switch, {
          value: allEnabled,
          onValueChange: toggleAll,
          trackColor: { true: colors.primary[500], false: colors.neutral[200] },
          thumbColor: '#FFFFFF',
          accessibilityLabel: 'Toggle all notifications',
        }),
      ),
    ),

    // Per-category toggles
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Notification categories' },
      React.createElement(Text, { style: styles.sectionTitle }, 'Categories'),
      ...NOTIFICATION_CATEGORIES.map((cat, idx) =>
        React.createElement(
          View,
          {
            key: cat.key,
            style: [
              styles.toggleRow,
              idx < NOTIFICATION_CATEGORIES.length - 1 ? styles.toggleRowBorder : null,
            ],
          },
          React.createElement(
            View,
            { style: styles.toggleTextGroup },
            React.createElement(Text, { style: styles.toggleLabel }, cat.label),
            React.createElement(Text, { style: styles.toggleDesc }, cat.description),
          ),
          React.createElement(Switch, {
            value: prefs[cat.key],
            onValueChange: () => toggleCategory(cat.key),
            trackColor: { true: colors.primary[500], false: colors.neutral[200] },
            thumbColor: '#FFFFFF',
            accessibilityLabel: `Toggle ${cat.label} notifications`,
          }),
        ),
      ),
    ),
  );
}

// Exported for testing
export { type ScreenState };

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

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
    backgroundColor: '#FFFFFF',
  },
  heading: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  savingText: {
    fontSize: typography.sizes.sm,
    color: colors.primary[600],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  card: {
    marginBottom: spacing.md,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[900],
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  masterLabel: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    minHeight: 44,
    paddingVertical: spacing.sm,
  },
  toggleRowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
  },
  toggleTextGroup: {
    flex: 1,
    marginRight: spacing.md,
  },
  toggleLabel: {
    fontSize: typography.sizes.base,
    fontWeight: '500',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  toggleDesc: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    marginTop: 2,
    fontFamily: typography.fontFamily,
  },
});
