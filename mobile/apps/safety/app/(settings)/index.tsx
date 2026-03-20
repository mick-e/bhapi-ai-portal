/**
 * Settings Screen
 *
 * Sections: Notifications, Language, Account, Push Permissions.
 * API: GET /api/v1/portal/settings
 * API: PUT /api/v1/portal/settings { notifications_enabled, language, ... }
 *
 * Push notification permissions use expo-notifications (registered at app startup).
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Switch,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Card, Button } from '@bhapi/ui';
import { tokenManager } from '@bhapi/auth';

interface SettingsData {
  notifications_enabled: boolean;
  push_enabled: boolean;
  email_digest: boolean;
  language: string;
}

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Espanol' },
  { code: 'fr', label: 'Francais' },
  { code: 'de', label: 'Deutsch' },
  { code: 'pt-BR', label: 'Portugues (BR)' },
  { code: 'it', label: 'Italiano' },
];

type SettingsState = 'loading' | 'loaded' | 'error';

export default function SettingsScreen() {
  const [state, setState] = useState<SettingsState>('loading');
  const [settings, setSettings] = useState<SettingsData>({
    notifications_enabled: true,
    push_enabled: false,
    email_digest: true,
    language: 'en',
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    try {
      setState('loading');
      // API call: GET /api/v1/portal/settings
      // const data = await apiClient.get<SettingsData>('/api/v1/portal/settings');
      // setSettings(data);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Failed to load settings.');
    }
  }

  async function saveSettings(updated: Partial<SettingsData>) {
    const newSettings = { ...settings, ...updated };
    setSettings(newSettings);

    try {
      setSaving(true);
      // API call: PUT /api/v1/portal/settings
      // await apiClient.put('/api/v1/portal/settings', newSettings);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to save settings.');
    } finally {
      setSaving(false);
    }
  }

  async function requestPushPermissions() {
    // In production: use expo-notifications to request permissions
    // const { status } = await Notifications.requestPermissionsAsync();
    // if (status === 'granted') saveSettings({ push_enabled: true });
    saveSettings({ push_enabled: true });
  }

  async function handleLogout() {
    await tokenManager.clearToken();
    // router.replace('/(auth)/login');
  }

  if (state === 'loading') {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading settings' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
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

    // Notifications section
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Notification settings' },
      React.createElement(
        Text,
        { style: styles.sectionTitle },
        'Notifications'
      ),
      renderToggle(
        'Push Notifications',
        settings.push_enabled,
        settings.push_enabled
          ? (val: boolean) => saveSettings({ push_enabled: val })
          : requestPushPermissions,
        !settings.push_enabled
          ? 'Tap to enable push notifications'
          : 'Toggle push notifications'
      ),
      renderToggle(
        'Alert Notifications',
        settings.notifications_enabled,
        (val: boolean) => saveSettings({ notifications_enabled: val }),
        'Toggle alert notifications'
      ),
      renderToggle(
        'Weekly Email Digest',
        settings.email_digest,
        (val: boolean) => saveSettings({ email_digest: val }),
        'Toggle weekly email digest'
      )
    ),

    // Language section
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Language settings' },
      React.createElement(
        Text,
        { style: styles.sectionTitle },
        'Language'
      ),
      ...LANGUAGES.map((lang) =>
        React.createElement(
          TouchableOpacity,
          {
            key: lang.code,
            style: [
              styles.languageOption,
              settings.language === lang.code ? styles.languageActive : null,
            ],
            onPress: () => saveSettings({ language: lang.code }),
            accessibilityRole: 'radio',
            accessibilityState: { selected: settings.language === lang.code },
            accessibilityLabel: lang.label,
          },
          React.createElement(
            Text,
            {
              style: [
                styles.languageText,
                settings.language === lang.code ? styles.languageTextActive : null,
              ],
            },
            lang.label
          ),
          settings.language === lang.code
            ? React.createElement(
                Text,
                { style: styles.checkIcon },
                '\u2713'
              )
            : null
        )
      )
    ),

    // Account section
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Account settings' },
      React.createElement(
        Text,
        { style: styles.sectionTitle },
        'Account'
      ),
      React.createElement(
        TouchableOpacity,
        {
          style: styles.accountOption,
          accessibilityLabel: 'Manage subscription',
          // onPress: () => router.push('/billing'),
        },
        React.createElement(
          Text,
          { style: styles.accountOptionText },
          'Manage Subscription'
        )
      ),
      React.createElement(
        TouchableOpacity,
        {
          style: styles.accountOption,
          accessibilityLabel: 'Privacy policy',
          // onPress: () => Linking.openURL('https://bhapi.ai/legal/privacy'),
        },
        React.createElement(
          Text,
          { style: styles.accountOptionText },
          'Privacy Policy'
        )
      ),
      React.createElement(
        TouchableOpacity,
        {
          style: styles.accountOption,
          accessibilityLabel: 'Terms of service',
        },
        React.createElement(
          Text,
          { style: styles.accountOptionText },
          'Terms of Service'
        )
      )
    ),

    // Error
    error
      ? React.createElement(
          Text,
          { style: styles.errorText, accessibilityRole: 'alert' },
          error
        )
      : null,

    // Logout
    React.createElement(Button, {
      title: 'Sign Out',
      onPress: handleLogout,
      variant: 'outline',
      style: styles.logoutButton,
      accessibilityLabel: 'Sign out',
    }),

    // Version info
    React.createElement(
      Text,
      { style: styles.versionText },
      'Bhapi Safety v0.1.0'
    )
  );
}

function renderToggle(
  label: string,
  value: boolean,
  onToggle: (val: boolean) => void,
  accessibilityLabel: string
) {
  return React.createElement(
    View,
    { key: label, style: styles.toggleRow },
    React.createElement(
      Text,
      { style: styles.toggleLabel },
      label
    ),
    React.createElement(Switch, {
      value,
      onValueChange: onToggle,
      trackColor: { true: colors.primary[500], false: colors.neutral[200] },
      thumbColor: '#FFFFFF',
      accessibilityLabel,
    })
  );
}

// Exported for testing
export { LANGUAGES, type SettingsData, type SettingsState };

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
    paddingVertical: spacing.sm,
    minHeight: 44,
  },
  toggleLabel: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
  },
  languageOption: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
    borderRadius: 8,
    minHeight: 44,
  },
  languageActive: {
    backgroundColor: colors.primary[50],
  },
  languageText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
  },
  languageTextActive: {
    color: colors.primary[700],
    fontWeight: '600',
  },
  checkIcon: {
    color: colors.primary[600],
    fontSize: typography.sizes.lg,
    fontWeight: '700',
  },
  accountOption: {
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
    minHeight: 44,
    justifyContent: 'center',
  },
  accountOptionText: {
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
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    textAlign: 'center',
    marginTop: spacing.sm,
    fontFamily: typography.fontFamily,
  },
});
