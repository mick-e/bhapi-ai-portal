import React from 'react';
import { View, Text, Image, TouchableOpacity, StyleSheet, ViewStyle, ImageSourcePropType } from 'react-native';
import { colors, typography } from '@bhapi/config';

export type AvatarSize = 'sm' | 'md' | 'lg';

export interface AvatarProps {
  name: string;
  source?: ImageSourcePropType;
  size?: AvatarSize;
  style?: ViewStyle;
  accessibilityLabel?: string;
  /** When provided, renders a tappable overlay for uploading a new avatar. */
  onUploadPress?: () => void;
  /** Show uploading indicator. */
  isUploading?: boolean;
}

export const avatarSizes: Record<AvatarSize, number> = {
  sm: 32,
  md: 48,
  lg: 64,
};

export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 0 || parts[0] === '') return '?';
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

export function Avatar({
  name,
  source,
  size = 'md',
  style,
  accessibilityLabel,
  onUploadPress,
  isUploading = false,
}: AvatarProps) {
  const dimension = avatarSizes[size];
  const fontSize = dimension * 0.4;

  const containerStyle: ViewStyle = {
    width: dimension,
    height: dimension,
    borderRadius: dimension / 2,
    minWidth: 44, // WCAG 2.1 AA for sm size
    minHeight: 44,
  };

  const avatarContent = source
    ? React.createElement(Image, {
        source,
        style: [
          containerStyle,
          { resizeMode: 'cover' },
          style,
        ] as any,
        accessibilityLabel: accessibilityLabel ?? name,
      })
    : React.createElement(
        View,
        {
          style: [
            styles.fallback,
            containerStyle,
            style,
          ],
          accessibilityLabel: accessibilityLabel ?? name,
        },
        React.createElement(
          Text,
          {
            style: [
              styles.initials,
              { fontSize },
            ],
          },
          getInitials(name)
        )
      );

  // Wrap with upload overlay when onUploadPress is provided
  if (onUploadPress) {
    return React.createElement(
      View,
      { style: styles.uploadContainer },
      avatarContent,
      React.createElement(
        TouchableOpacity,
        {
          onPress: onUploadPress,
          style: [styles.uploadOverlay, containerStyle],
          accessibilityLabel: isUploading ? 'Uploading avatar' : 'Upload avatar',
          accessibilityRole: 'button',
          disabled: isUploading,
        },
        React.createElement(
          View,
          { style: styles.uploadBadge },
          React.createElement(
            Text,
            { style: styles.uploadBadgeText },
            isUploading ? '...' : '+'
          )
        )
      )
    );
  }

  return avatarContent;
}

const styles = StyleSheet.create({
  fallback: {
    backgroundColor: colors.primary[500],
    alignItems: 'center',
    justifyContent: 'center',
  },
  initials: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
  uploadContainer: {
    position: 'relative',
  },
  uploadOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    alignItems: 'center',
    justifyContent: 'flex-end',
  },
  uploadBadge: {
    backgroundColor: colors.primary[600],
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: '#FFFFFF',
    marginBottom: 2,
  },
  uploadBadgeText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
});
