/**
 * Social App Settings Screen
 *
 * Simpler than Safety settings. Privacy, notifications, account.
 * API: GET /api/v1/social/profile/settings
 * API: PUT /api/v1/social/profile/settings
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  Switch,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Card, Button } from '@bhapi/ui';
import { tokenManager } from '@bhapi/auth';

interface SocialSettings {
  notifications_enabled: boolean;
  profile_visibility: 'friends' | 'public';
  allow_messages_from: 'friends' | 'everyone';
}

export default function SocialSettingsScreen() {
  const [settings, setSettings] = useState<SocialSettings>({
    notifications_enabled: true,
    profile_visibility: 'friends',
    allow_messages_from: 'friends',
  });

  function updateSetting<K extends keyof SocialSettings>(
    key: K,
    value: SocialSettings[K]
  ) {
    setSettings((prev) => ({ ...prev, [key]: value }));
    // API call: PUT /api/v1/social/profile/settings
    // apiClient.put('/api/v1/social/profile/settings', { ...settings, [key]: value });
  }

  async function handleLogout() {
    await tokenManager.clearToken();
    // router.replace('/(auth)/login');
  }

  return React.createElement(
    ScrollView,
    {
      style: styles.container,
      contentContainerStyle: styles.content,
      accessibilityLabel: 'Settings',
    },
    React.createElement(
      Text,
      { style: styles.heading, accessibilityRole: 'header' },
      'Settings'
    ),

    // Notifications
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Notifications' },
      React.createElement(Text, { style: styles.sectionTitle }, 'Notifications'),
      React.createElement(
        View,
        { style: styles.toggleRow },
        React.createElement(Text, { style: styles.toggleLabel }, 'Notifications'),
        React.createElement(Switch, {
          value: settings.notifications_enabled,
          onValueChange: (val: boolean) => updateSetting('notifications_enabled', val),
          trackColor: { true: colors.primary[500], false: colors.neutral[200] },
          thumbColor: '#FFFFFF',
          accessibilityLabel: 'Toggle notifications',
        })
      )
    ),

    // Privacy
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Privacy settings' },
      React.createElement(Text, { style: styles.sectionTitle }, 'Privacy'),
      React.createElement(
        Text,
        { style: styles.optionLabel },
        'Who can see my profile?'
      ),
      renderRadio('Friends only', settings.profile_visibility === 'friends', () =>
        updateSetting('profile_visibility', 'friends')
      ),
      renderRadio('Everyone', settings.profile_visibility === 'public', () =>
        updateSetting('profile_visibility', 'public')
      ),
      React.createElement(
        Text,
        { style: [styles.optionLabel, { marginTop: spacing.md }] },
        'Who can message me?'
      ),
      renderRadio('Friends only', settings.allow_messages_from === 'friends', () =>
        updateSetting('allow_messages_from', 'friends')
      ),
      renderRadio('Everyone', settings.allow_messages_from === 'everyone', () =>
        updateSetting('allow_messages_from', 'everyone')
      )
    ),

    // Help
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Help' },
      React.createElement(Text, { style: styles.sectionTitle }, 'Help'),
      React.createElement(
        TouchableOpacity,
        {
          style: styles.helpOption,
          accessibilityLabel: 'Report a problem',
        },
        React.createElement(
          Text,
          { style: styles.helpOptionText },
          'Report a Problem'
        )
      ),
      React.createElement(
        TouchableOpacity,
        {
          style: styles.helpOption,
          accessibilityLabel: 'Safety tips',
        },
        React.createElement(
          Text,
          { style: styles.helpOptionText },
          'Safety Tips'
        )
      )
    ),

    // Sign out
    React.createElement(Button, {
      title: 'Sign Out',
      onPress: handleLogout,
      variant: 'outline',
      style: styles.logoutButton,
      accessibilityLabel: 'Sign out',
    }),

    React.createElement(
      Text,
      { style: styles.versionText },
      'Bhapi Social v0.1.0'
    )
  );
}

function renderRadio(label: string, selected: boolean, onPress: () => void) {
  return React.createElement(
    TouchableOpacity,
    {
      key: label,
      style: styles.radioRow,
      onPress,
      accessibilityRole: 'radio',
      accessibilityState: { selected },
      accessibilityLabel: label,
    },
    React.createElement(
      View,
      { style: [styles.radioOuter, selected ? styles.radioOuterSelected : null] },
      selected
        ? React.createElement(View, { style: styles.radioInner })
        : null
    ),
    React.createElement(
      Text,
      { style: styles.radioLabel },
      label
    )
  );
}

// Exported for testing
export { type SocialSettings };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  content: {
    padding: spacing.md,
    paddingBottom: spacing['2xl'],
  },
  heading: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    marginBottom: spacing.md,
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
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    minHeight: 44,
  },
  toggleLabel: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
  },
  optionLabel: {
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    color: colors.neutral[700],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  radioRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    minHeight: 44,
  },
  radioOuter: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: colors.neutral[200],
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.sm,
  },
  radioOuterSelected: {
    borderColor: colors.primary[600],
  },
  radioInner: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: colors.primary[600],
  },
  radioLabel: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
  },
  helpOption: {
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
    minHeight: 44,
    justifyContent: 'center',
  },
  helpOptionText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
  },
  logoutButton: {
    marginTop: spacing.lg,
  },
  versionText: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    textAlign: 'center',
    marginTop: spacing.lg,
    fontFamily: typography.fontFamily,
  },
});
