import React from 'react';
import { Image, View, StyleSheet, ViewStyle, ImageSourcePropType } from 'react-native';
import { colors } from '@bhapi/config';

export type LogoSize = 'sm' | 'md' | 'lg';

export interface BhapiLogoProps {
  size?: LogoSize;
  source?: ImageSourcePropType;
  style?: ViewStyle;
  accessibilityLabel?: string;
}

export const logoSizes: Record<LogoSize, { width: number; height: number }> = {
  sm: { width: 80, height: 28 },
  md: { width: 120, height: 42 },
  lg: { width: 180, height: 63 },
};

/**
 * Renders the Bhapi logo as a PNG image.
 * Per CLAUDE.md: NEVER use SVG logos — brand assets are PNG only.
 * Brand orange: #FF6B35
 */
export function BhapiLogo({
  size = 'md',
  source,
  style,
  accessibilityLabel = 'Bhapi',
}: BhapiLogoProps) {
  const dimensions = logoSizes[size];

  // If no source provided, render a placeholder with brand color
  if (!source) {
    return React.createElement(
      View,
      {
        style: [
          styles.placeholder,
          {
            width: dimensions.width,
            height: dimensions.height,
            minHeight: 44, // WCAG 2.1 AA
          },
          style,
        ],
        accessibilityLabel,
      }
    );
  }

  return React.createElement(Image, {
    source,
    style: [
      {
        width: dimensions.width,
        height: dimensions.height,
        resizeMode: 'contain',
      },
      style,
    ] as any,
    accessibilityLabel,
  });
}

const styles = StyleSheet.create({
  placeholder: {
    backgroundColor: colors.primary[500],
    borderRadius: 4,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
