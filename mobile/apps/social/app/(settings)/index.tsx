/**
 * Social App Settings Screen
 *
 * Section list: Privacy, Notifications, Language, Theme (light/dark), Account (logout, delete).
 * Each section links to its dedicated sub-screen or toggles inline.
 *
 * API: GET /api/v1/social/profile/settings
 * API: PUT /api/v1/social/profile/settings
 * API: DELETE /api/v1/auth/account (delete account)
 */
import React, { useState, useCallback } from 'react';
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

// ---------------------------------------------------------------------------
// Types & Constants
// ---------------------------------------------------------------------------

export type ThemeMode = 'light' | 'dark' | 'system';

export type SupportedLanguage = 'en' | 'fr' | 'es' | 'de' | 'pt-BR' | 'it';

export interface SocialSettings {
  notifications_enabled: boolean;
  profile_visibility: 'friends' | 'public' | 'private';
  allow_messages_from: 'friends' | 'everyone' | 'nobody';
  show_online_status: boolean;
  theme: ThemeMode;
  language: SupportedLanguage;
}

export const DEFAULT_SETTINGS: SocialSettings = {
  notifications_enabled: true,
  profile_visibility: 'friends',
  allow_messages_from: 'friends',
  show_online_status: true,
  theme: 'system',
  language: 'en',
};

export const THEME_OPTIONS: { value: ThemeMode; label: string }[] = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System Default' },
];

export const LANGUAGE_OPTIONS: { value: SupportedLanguage; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'Fran\u00e7ais' },
  { value: 'es', label: 'Espa\u00f1ol' },
  { value: 'de', label: 'Deutsch' },
  { value: 'pt-BR', label: 'Portugu\u00eas (Brasil)' },
  { value: 'it', label: 'Italiano' },
];

export const SETTINGS_SECTIONS = [
  'privacy',
  'notifications',
  'language',
  'theme',
  'account',
] as const;

export type SettingsSection = (typeof SETTINGS_SECTIONS)[number];

type ScreenState = 'idle' | 'confirming_delete' | 'deleting';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SocialSettingsScreen() {
  const [settings, setSettings] = useState<SocialSettings>(DEFAULT_SETTINGS);
  const [screenState, setScreenState] = useState<ScreenState>('idle');
  const [deleteError, setDeleteError] = useState<string | null>(null);

  function updateSetting<K extends keyof SocialSettings>(
    key: K,
    value: SocialSettings[K],
  ) {
    setSettings((prev) => ({ ...prev, [key]: value }));
    // API: PUT /api/v1/social/profile/settings
    // apiClient.put('/api/v1/social/profile/settings', { ...settings, [key]: value });
  }

  const handleLogout = useCallback(async () => {
    await tokenManager.clearToken();
    // router.replace('/(auth)/login');
  }, []);

  const handleDeleteRequest = useCallback(() => {
    setScreenState('confirming_delete');
    setDeleteError(null);
  }, []);

  const handleDeleteCancel = useCallback(() => {
    setScreenState('idle');
    setDeleteError(null);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    try {
      setScreenState('deleting');
      // API: DELETE /api/v1/auth/account
      // await apiClient.delete('/api/v1/auth/account');
      await tokenManager.clearToken();
      // router.replace('/(auth)/login');
    } catch (e: any) {
      setDeleteError(e?.message ?? 'Could not delete account. Please try again.');
      setScreenState('idle');
    }
  }, []);

  function handleNavigateToPrivacy() {
    // router.push('/(settings)/privacy');
  }

  function handleNavigateToNotifications() {
    // router.push('/(settings)/notifications');
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
      'Settings',
    ),

    // -----------------------------------------------------------------------
    // Privacy Section
    // -----------------------------------------------------------------------
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Privacy settings' },
      React.createElement(
        TouchableOpacity,
        {
          style: styles.navRow,
          onPress: handleNavigateToPrivacy,
          accessibilityLabel: 'Open privacy settings',
          accessibilityRole: 'button',
        },
        React.createElement(
          View,
          { style: styles.navRowContent },
          React.createElement(Text, { style: styles.sectionTitle }, 'Privacy'),
          React.createElement(
            Text,
            { style: styles.sectionDesc },
            'Who can see your profile and message you',
          ),
        ),
        React.createElement(Text, { style: styles.chevron }, '\u203A'),
      ),
    ),

    // -----------------------------------------------------------------------
    // Notifications Section
    // -----------------------------------------------------------------------
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Notification settings' },
      React.createElement(
        TouchableOpacity,
        {
          style: styles.navRow,
          onPress: handleNavigateToNotifications,
          accessibilityLabel: 'Open notification settings',
          accessibilityRole: 'button',
        },
        React.createElement(
          View,
          { style: styles.navRowContent },
          React.createElement(Text, { style: styles.sectionTitle }, 'Notifications'),
          React.createElement(
            Text,
            { style: styles.sectionDesc },
            'Manage push notification preferences',
          ),
        ),
        React.createElement(Text, { style: styles.chevron }, '\u203A'),
      ),
    ),

    // -----------------------------------------------------------------------
    // Language Section
    // -----------------------------------------------------------------------
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Language settings' },
      React.createElement(Text, { style: styles.sectionTitle }, 'Language'),
      React.createElement(
        Text,
        { style: styles.sectionDesc },
        'Choose your preferred language',
      ),
      ...LANGUAGE_OPTIONS.map((option) =>
        renderRadio(
          option.label,
          settings.language === option.value,
          () => updateSetting('language', option.value),
        ),
      ),
    ),

    // -----------------------------------------------------------------------
    // Theme Section
    // -----------------------------------------------------------------------
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Theme settings' },
      React.createElement(Text, { style: styles.sectionTitle }, 'Theme'),
      React.createElement(
        Text,
        { style: styles.sectionDesc },
        'Choose light or dark mode',
      ),
      ...THEME_OPTIONS.map((option) =>
        renderRadio(
          option.label,
          settings.theme === option.value,
          () => updateSetting('theme', option.value),
        ),
      ),
    ),

    // -----------------------------------------------------------------------
    // Account Section
    // -----------------------------------------------------------------------
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Account' },
      React.createElement(Text, { style: styles.sectionTitle }, 'Account'),

      // Sign out
      React.createElement(Button, {
        title: 'Sign Out',
        onPress: handleLogout,
        variant: 'outline',
        style: styles.accountButton,
        accessibilityLabel: 'Sign out',
      }),

      // Delete account
      screenState === 'confirming_delete'
        ? React.createElement(
            View,
            { style: styles.deleteConfirm, accessibilityLabel: 'Confirm account deletion' },
            React.createElement(
              Text,
              { style: styles.deleteWarning, accessibilityRole: 'alert' },
              'Are you sure? This action cannot be undone. All your data will be permanently deleted.',
            ),
            React.createElement(
              View,
              { style: styles.deleteActions },
              React.createElement(
                TouchableOpacity,
                {
                  onPress: handleDeleteCancel,
                  style: styles.cancelButton,
                  accessibilityLabel: 'Cancel deletion',
                },
                React.createElement(
                  Text,
                  { style: styles.cancelButtonText },
                  'Cancel',
                ),
              ),
              React.createElement(
                TouchableOpacity,
                {
                  onPress: handleDeleteConfirm,
                  style: styles.confirmDeleteButton,
                  accessibilityLabel: 'Confirm delete account',
                },
                React.createElement(
                  Text,
                  { style: styles.confirmDeleteText },
                  'Delete Account',
                ),
              ),
            ),
          )
        : React.createElement(
            TouchableOpacity,
            {
              onPress: handleDeleteRequest,
              style: styles.deleteButton,
              accessibilityLabel: 'Delete account',
            },
            React.createElement(
              Text,
              { style: styles.deleteButtonText },
              screenState === 'deleting' ? 'Deleting...' : 'Delete Account',
            ),
          ),

      deleteError
        ? React.createElement(
            Text,
            { style: styles.deleteError, accessibilityRole: 'alert' },
            deleteError,
          )
        : null,
    ),

    // -----------------------------------------------------------------------
    // Help
    // -----------------------------------------------------------------------
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
          'Report a Problem',
        ),
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
          'Safety Tips',
        ),
      ),
    ),

    // Version
    React.createElement(
      Text,
      { style: styles.versionText },
      'Bhapi Social v0.2.0',
    ),
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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
        : null,
    ),
    React.createElement(
      Text,
      { style: styles.radioLabel },
      label,
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
    fontFamily: typography.fontFamily,
  },
  sectionDesc: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    marginTop: 2,
    fontFamily: typography.fontFamily,
  },
  navRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    minHeight: 44,
  },
  navRowContent: {
    flex: 1,
  },
  chevron: {
    fontSize: typography.sizes['2xl'],
    color: colors.neutral[500],
    paddingLeft: spacing.md,
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
  accountButton: {
    marginTop: spacing.md,
  },
  deleteButton: {
    marginTop: spacing.md,
    minHeight: 44,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  deleteButtonText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.base,
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  deleteConfirm: {
    marginTop: spacing.md,
    padding: spacing.md,
    backgroundColor: colors.neutral[50],
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.semantic.error,
  },
  deleteWarning: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  deleteActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 12,
  },
  cancelButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
  },
  cancelButtonText: {
    color: colors.neutral[700],
    fontSize: typography.sizes.base,
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  confirmDeleteButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    backgroundColor: colors.semantic.error,
    borderRadius: 8,
  },
  confirmDeleteText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  deleteError: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    marginTop: spacing.sm,
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
  versionText: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    textAlign: 'center',
    marginTop: spacing.lg,
    fontFamily: typography.fontFamily,
  },
});
