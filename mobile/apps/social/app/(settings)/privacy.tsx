/**
 * Privacy Settings Screen
 *
 * Controls who can see the user's profile, who can message them,
 * and whether online status is visible.
 *
 * API: GET /api/v1/social/profiles/me
 * API: PUT /api/v1/social/profiles/me
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  Switch,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Card } from '@bhapi/ui';

// ---------------------------------------------------------------------------
// Types & Constants
// ---------------------------------------------------------------------------

export type ProfileVisibilitySetting = 'everyone' | 'friends' | 'nobody';
export type MessagePermission = 'friends' | 'nobody';

export interface PrivacySettings {
  profile_visibility: ProfileVisibilitySetting;
  allow_messages_from: MessagePermission;
  show_online_status: boolean;
}

export const DEFAULT_PRIVACY_SETTINGS: PrivacySettings = {
  profile_visibility: 'friends',
  allow_messages_from: 'friends',
  show_online_status: true,
};

export const PROFILE_VISIBILITY_OPTIONS: {
  value: ProfileVisibilitySetting;
  label: string;
  description: string;
}[] = [
  { value: 'everyone', label: 'Everyone', description: 'Anyone on Bhapi can see your profile' },
  { value: 'friends', label: 'Friends Only', description: 'Only your friends can see your profile' },
  { value: 'nobody', label: 'Nobody', description: 'Your profile is hidden from everyone' },
];

export const MESSAGE_PERMISSION_OPTIONS: {
  value: MessagePermission;
  label: string;
  description: string;
}[] = [
  { value: 'friends', label: 'Friends Only', description: 'Only friends can send you messages' },
  { value: 'nobody', label: 'Nobody', description: 'No one can send you messages' },
];

type ScreenState = 'loading' | 'idle' | 'saving' | 'error';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PrivacySettingsScreen() {
  const [state, setState] = useState<ScreenState>('loading');
  const [settings, setSettings] = useState<PrivacySettings>(DEFAULT_PRIVACY_SETTINGS);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    try {
      setState('loading');
      // API: GET /api/v1/social/profiles/me -> extract privacy fields
      // const profile = await apiClient.get('/api/v1/social/profiles/me');
      // setSettings({
      //   profile_visibility: mapVisibility(profile.visibility),
      //   allow_messages_from: profile.allow_messages_from ?? 'friends',
      //   show_online_status: profile.show_online_status ?? true,
      // });
      setState('idle');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Could not load privacy settings.');
    }
  }

  const updateSetting = useCallback(
    async <K extends keyof PrivacySettings>(key: K, value: PrivacySettings[K]) => {
      const updated = { ...settings, [key]: value };
      setSettings(updated);
      try {
        setState('saving');
        // API: PUT /api/v1/social/profiles/me
        // await apiClient.put('/api/v1/social/profiles/me', {
        //   visibility: mapToApiVisibility(updated.profile_visibility),
        //   allow_messages_from: updated.allow_messages_from,
        //   show_online_status: updated.show_online_status,
        // });
        setState('idle');
      } catch (e: any) {
        setState('error');
        setError(e?.message ?? 'Could not save privacy setting.');
      }
    },
    [settings],
  );

  if (state === 'loading') {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading privacy settings' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      }),
    );
  }

  if (state === 'error' && !settings) {
    return React.createElement(
      View,
      { style: styles.centered },
      React.createElement(
        Text,
        { style: styles.errorText, accessibilityRole: 'alert' },
        error,
      ),
      React.createElement(
        TouchableOpacity,
        { onPress: loadSettings, style: styles.retryButton },
        React.createElement(Text, { style: styles.retryText }, 'Try again'),
      ),
    );
  }

  return React.createElement(
    ScrollView,
    {
      style: styles.container,
      contentContainerStyle: styles.content,
      accessibilityLabel: 'Privacy Settings',
    },

    // Header
    React.createElement(
      Text,
      { style: styles.heading, accessibilityRole: 'header' },
      'Privacy',
    ),

    // Saving indicator
    state === 'saving'
      ? React.createElement(
          Text,
          { style: styles.savingText, accessibilityRole: 'alert' },
          'Saving...',
        )
      : null,

    // Who can see my profile
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Profile visibility' },
      React.createElement(Text, { style: styles.sectionTitle }, 'Who can see my profile?'),
      React.createElement(
        Text,
        { style: styles.sectionDesc },
        'Control who can view your profile and posts.',
      ),
      ...PROFILE_VISIBILITY_OPTIONS.map((option) =>
        renderRadioOption(
          option.value,
          option.label,
          option.description,
          settings.profile_visibility === option.value,
          () => updateSetting('profile_visibility', option.value),
        ),
      ),
    ),

    // Who can message me
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Message permissions' },
      React.createElement(Text, { style: styles.sectionTitle }, 'Who can message me?'),
      React.createElement(
        Text,
        { style: styles.sectionDesc },
        'Control who can send you direct messages.',
      ),
      ...MESSAGE_PERMISSION_OPTIONS.map((option) =>
        renderRadioOption(
          option.value,
          option.label,
          option.description,
          settings.allow_messages_from === option.value,
          () => updateSetting('allow_messages_from', option.value),
        ),
      ),
    ),

    // Online status
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Online status' },
      React.createElement(Text, { style: styles.sectionTitle }, 'Online Status'),
      React.createElement(
        View,
        { style: styles.toggleRow },
        React.createElement(
          View,
          { style: styles.toggleTextGroup },
          React.createElement(Text, { style: styles.toggleLabel }, 'Show when I\'m online'),
          React.createElement(
            Text,
            { style: styles.toggleDesc },
            'Let friends see when you are active.',
          ),
        ),
        React.createElement(Switch, {
          value: settings.show_online_status,
          onValueChange: (val: boolean) => updateSetting('show_online_status', val),
          trackColor: { true: colors.primary[500], false: colors.neutral[200] },
          thumbColor: '#FFFFFF',
          accessibilityLabel: 'Toggle online status visibility',
        }),
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderRadioOption(
  key: string,
  label: string,
  description: string,
  selected: boolean,
  onPress: () => void,
) {
  return React.createElement(
    TouchableOpacity,
    {
      key,
      style: [styles.radioRow, selected ? styles.radioRowSelected : null],
      onPress,
      accessibilityRole: 'radio',
      accessibilityState: { selected },
      accessibilityLabel: `${label}: ${description}`,
    },
    React.createElement(
      View,
      { style: [styles.radioOuter, selected ? styles.radioOuterSelected : null] },
      selected ? React.createElement(View, { style: styles.radioInner }) : null,
    ),
    React.createElement(
      View,
      { style: styles.radioTextGroup },
      React.createElement(Text, { style: styles.radioLabel }, label),
      React.createElement(Text, { style: styles.radioDesc }, description),
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
  card: {
    marginBottom: spacing.md,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[900],
    marginBottom: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  sectionDesc: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  radioRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
    borderRadius: 8,
    minHeight: 44,
  },
  radioRowSelected: {
    backgroundColor: colors.primary[50],
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
    marginTop: 2,
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
  radioTextGroup: {
    flex: 1,
  },
  radioLabel: {
    fontSize: typography.sizes.base,
    fontWeight: '500',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  radioDesc: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    marginTop: 2,
    fontFamily: typography.fontFamily,
  },
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    minHeight: 44,
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
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.base,
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  retryButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  retryText: {
    color: colors.primary[700],
    fontSize: typography.sizes.base,
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
});
