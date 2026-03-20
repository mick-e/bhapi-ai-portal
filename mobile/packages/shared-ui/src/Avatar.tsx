import React from 'react';
import { View, Text, Image, StyleSheet, ViewStyle, ImageSourcePropType } from 'react-native';
import { colors, typography } from '@bhapi/config';

export type AvatarSize = 'sm' | 'md' | 'lg';

export interface AvatarProps {
  name: string;
  source?: ImageSourcePropType;
  size?: AvatarSize;
  style?: ViewStyle;
  accessibilityLabel?: string;
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

  if (source) {
    return React.createElement(Image, {
      source,
      style: [
        containerStyle,
        { resizeMode: 'cover' },
        style,
      ] as any,
      accessibilityLabel: accessibilityLabel ?? name,
    });
  }

  return React.createElement(
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
});
