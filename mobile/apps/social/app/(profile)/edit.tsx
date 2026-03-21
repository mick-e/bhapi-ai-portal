/**
 * Profile Edit Screen — edit display name, bio, avatar, visibility.
 *
 * Avatar: camera/gallery via expo-image-picker -> upload to media API -> set avatar_url.
 * API: PUT /api/v1/social/profiles/me
 * API: POST /api/v1/media/upload (avatar)
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  TextInput,
  ActivityIndicator,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Avatar, Button, Input } from '@bhapi/ui';
import type { Profile, ProfileVisibility } from '@bhapi/types';

type EditState = 'idle' | 'loading' | 'saving' | 'saved' | 'error';

// Validation constants (exported for testing)
export const MAX_DISPLAY_NAME_LENGTH = 255;
export const MIN_DISPLAY_NAME_LENGTH = 1;
export const MAX_BIO_LENGTH = 500;
export const VISIBILITY_OPTIONS: { value: ProfileVisibility; label: string }[] = [
  { value: 'public', label: 'Public' },
  { value: 'friends_only', label: 'Friends Only' },
  { value: 'private', label: 'Private' },
];

/**
 * Validate profile form fields.
 * Returns null if valid, or an error message string.
 */
export function validateProfileForm(
  displayName: string,
  bio: string,
): string | null {
  const trimmed = displayName.trim();
  if (trimmed.length < MIN_DISPLAY_NAME_LENGTH) {
    return 'Display name is required';
  }
  if (trimmed.length > MAX_DISPLAY_NAME_LENGTH) {
    return `Display name must be ${MAX_DISPLAY_NAME_LENGTH} characters or less`;
  }
  if (bio.length > MAX_BIO_LENGTH) {
    return `Bio must be ${MAX_BIO_LENGTH} characters or less`;
  }
  return null;
}

export default function EditProfileScreen() {
  const [state, setState] = useState<EditState>('loading');
  const [error, setError] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [bio, setBio] = useState('');
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [visibility, setVisibility] = useState<ProfileVisibility>('friends_only');
  const [isUploading, setIsUploading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    loadProfile();
  }, []);

  async function loadProfile() {
    try {
      setState('loading');
      // API call: GET /api/v1/social/profiles/me
      // const profile = await apiClient.get<Profile>('/api/v1/social/profiles/me');
      // setDisplayName(profile.display_name);
      // setBio(profile.bio ?? '');
      // setAvatarUrl(profile.avatar_url);
      // setVisibility(profile.visibility ?? 'friends_only');
      setState('idle');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Could not load profile.');
    }
  }

  const handlePickAvatar = useCallback(async () => {
    try {
      setIsUploading(true);
      // In production:
      // const result = await ImagePicker.launchImageLibraryAsync({
      //   mediaTypes: ImagePicker.MediaTypeOptions.Images,
      //   allowsEditing: true,
      //   aspect: [1, 1],
      //   quality: 0.8,
      // });
      // if (!result.canceled) {
      //   const formData = new FormData();
      //   formData.append('file', { uri: result.assets[0].uri, ... });
      //   const uploaded = await apiClient.post('/api/v1/media/upload', formData);
      //   setAvatarUrl(uploaded.url);
      // }
    } catch (e: any) {
      setFormError('Failed to upload avatar');
    } finally {
      setIsUploading(false);
    }
  }, []);

  const handleSave = useCallback(async () => {
    const validationError = validateProfileForm(displayName, bio);
    if (validationError) {
      setFormError(validationError);
      return;
    }

    try {
      setState('saving');
      setFormError(null);
      // API call: PUT /api/v1/social/profiles/me
      // await apiClient.put('/api/v1/social/profiles/me', {
      //   display_name: displayName.trim(),
      //   bio: bio.trim() || null,
      //   avatar_url: avatarUrl,
      //   visibility,
      // });
      setState('saved');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Could not save profile.');
    }
  }, [displayName, bio, avatarUrl, visibility]);

  if (state === 'loading') {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading profile' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  if (state === 'error' && !displayName) {
    return React.createElement(
      View,
      { style: styles.centered },
      React.createElement(
        Text,
        { style: styles.errorText, accessibilityRole: 'alert' },
        error
      ),
      React.createElement(
        TouchableOpacity,
        { onPress: loadProfile, style: styles.retryButton },
        React.createElement(Text, { style: styles.retryText }, 'Try again')
      )
    );
  }

  return React.createElement(
    ScrollView,
    {
      style: styles.container,
      contentContainerStyle: styles.content,
      accessibilityLabel: 'Edit Profile',
    },

    // Header
    React.createElement(
      Text,
      { style: styles.header, accessibilityRole: 'header' },
      'Edit Profile'
    ),

    // Avatar with upload button
    React.createElement(
      View,
      { style: styles.avatarSection },
      React.createElement(Avatar, {
        name: displayName || '?',
        size: 'lg',
        ...(avatarUrl ? { source: { uri: avatarUrl } } : {}),
      }),
      React.createElement(
        TouchableOpacity,
        {
          onPress: handlePickAvatar,
          style: styles.changeAvatarButton,
          accessibilityLabel: 'Change avatar',
          accessibilityRole: 'button',
          disabled: isUploading,
        },
        React.createElement(
          Text,
          { style: styles.changeAvatarText },
          isUploading ? 'Uploading...' : 'Change Photo'
        )
      )
    ),

    // Form error
    formError
      ? React.createElement(
          Text,
          { style: styles.formError, accessibilityRole: 'alert' },
          formError
        )
      : null,

    // Success message
    state === 'saved'
      ? React.createElement(
          Text,
          { style: styles.successText, accessibilityRole: 'alert' },
          'Profile saved!'
        )
      : null,

    // Display name
    React.createElement(
      View,
      { style: styles.fieldGroup },
      React.createElement(
        Text,
        { style: styles.label },
        'Display Name'
      ),
      React.createElement(TextInput, {
        style: styles.textInput,
        value: displayName,
        onChangeText: setDisplayName,
        maxLength: MAX_DISPLAY_NAME_LENGTH,
        accessibilityLabel: 'Display name',
        placeholder: 'Your display name',
      }),
      React.createElement(
        Text,
        { style: styles.charCount },
        `${displayName.length}/${MAX_DISPLAY_NAME_LENGTH}`
      )
    ),

    // Bio
    React.createElement(
      View,
      { style: styles.fieldGroup },
      React.createElement(
        Text,
        { style: styles.label },
        'Bio'
      ),
      React.createElement(TextInput, {
        style: [styles.textInput, styles.bioInput],
        value: bio,
        onChangeText: setBio,
        maxLength: MAX_BIO_LENGTH,
        multiline: true,
        numberOfLines: 4,
        accessibilityLabel: 'Bio',
        placeholder: 'Tell us about yourself',
      }),
      React.createElement(
        Text,
        { style: styles.charCount },
        `${bio.length}/${MAX_BIO_LENGTH}`
      )
    ),

    // Visibility selector
    React.createElement(
      View,
      { style: styles.fieldGroup },
      React.createElement(
        Text,
        { style: styles.label },
        'Profile Visibility'
      ),
      ...VISIBILITY_OPTIONS.map((option) =>
        React.createElement(
          TouchableOpacity,
          {
            key: option.value,
            style: [
              styles.visibilityOption,
              visibility === option.value ? styles.visibilitySelected : null,
            ],
            onPress: () => setVisibility(option.value),
            accessibilityLabel: `${option.label} visibility`,
            accessibilityRole: 'radio',
            accessibilityState: { selected: visibility === option.value },
          },
          React.createElement(
            View,
            { style: styles.radioOuter },
            visibility === option.value
              ? React.createElement(View, { style: styles.radioInner })
              : null
          ),
          React.createElement(
            Text,
            { style: styles.visibilityLabel },
            option.label
          )
        )
      )
    ),

    // Save button
    React.createElement(
      TouchableOpacity,
      {
        onPress: handleSave,
        style: styles.saveButton,
        accessibilityLabel: 'Save profile',
        accessibilityRole: 'button',
        disabled: state === 'saving',
      },
      React.createElement(
        Text,
        { style: styles.saveButtonText },
        state === 'saving' ? 'Saving...' : 'Save Profile'
      )
    )
  );
}

// Exported for testing
export { type EditState };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  content: {
    padding: spacing.lg,
    paddingTop: spacing.xl,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
  },
  header: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    marginBottom: spacing.lg,
    fontFamily: typography.fontFamily,
  },
  avatarSection: {
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  changeAvatarButton: {
    marginTop: spacing.sm,
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
  },
  changeAvatarText: {
    color: colors.primary[700],
    fontSize: typography.sizes.base,
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  fieldGroup: {
    marginBottom: spacing.lg,
  },
  label: {
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    color: colors.neutral[700],
    marginBottom: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  textInput: {
    borderWidth: 1,
    borderColor: colors.neutral[300],
    borderRadius: 8,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: typography.sizes.base,
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
    minHeight: 44,
  },
  bioInput: {
    minHeight: 100,
    textAlignVertical: 'top',
  },
  charCount: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[400],
    textAlign: 'right',
    marginTop: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  visibilityOption: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: 8,
    marginBottom: spacing.xs,
    minHeight: 44,
  },
  visibilitySelected: {
    backgroundColor: colors.primary[50],
  },
  radioOuter: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.primary[600],
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.sm,
  },
  radioInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.primary[600],
  },
  visibilityLabel: {
    fontSize: typography.sizes.base,
    color: colors.neutral[800],
    fontFamily: typography.fontFamily,
  },
  saveButton: {
    backgroundColor: colors.primary[600],
    borderRadius: 8,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
    marginTop: spacing.md,
  },
  saveButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  formError: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  successText: {
    color: colors.semantic.success,
    fontSize: typography.sizes.sm,
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
