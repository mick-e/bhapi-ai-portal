import React from 'react';
import {
  TouchableOpacity,
  Text,
  ActivityIndicator,
  StyleSheet,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

export type ButtonVariant = 'primary' | 'secondary' | 'outline';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  disabled?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  accessibilityLabel?: string;
}

const sizeStyles: Record<ButtonSize, { height: number; paddingHorizontal: number; fontSize: number }> = {
  sm: { height: 44, paddingHorizontal: spacing.md, fontSize: typography.sizes.sm },
  md: { height: 48, paddingHorizontal: spacing.lg, fontSize: typography.sizes.base },
  lg: { height: 56, paddingHorizontal: spacing.xl, fontSize: typography.sizes.lg },
};

const variantStyles: Record<ButtonVariant, { bg: string; text: string; border?: string }> = {
  primary: { bg: colors.primary[600], text: '#FFFFFF' },
  secondary: { bg: colors.accent[500], text: '#FFFFFF' },
  outline: { bg: 'transparent', text: colors.primary[700], border: colors.primary[600] },
};

export function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  style,
  textStyle,
  accessibilityLabel,
}: ButtonProps) {
  const sizeConfig = sizeStyles[size];
  const variantConfig = variantStyles[variant];

  return React.createElement(
    TouchableOpacity,
    {
      onPress,
      disabled: disabled || isLoading,
      accessibilityLabel: accessibilityLabel ?? title,
      accessibilityRole: 'button',
      style: [
        styles.base,
        {
          height: sizeConfig.height,
          minHeight: 44, // WCAG 2.1 AA minimum tap target
          minWidth: 44,
          paddingHorizontal: sizeConfig.paddingHorizontal,
          backgroundColor: variantConfig.bg,
          borderColor: variantConfig.border ?? 'transparent',
          borderWidth: variantConfig.border ? 2 : 0,
          opacity: disabled ? 0.5 : 1,
        },
        style,
      ],
    },
    isLoading
      ? React.createElement(ActivityIndicator, {
          color: variantConfig.text,
          size: 'small',
        })
      : React.createElement(
          Text,
          {
            style: [
              styles.text,
              {
                color: variantConfig.text,
                fontSize: sizeConfig.fontSize,
                fontFamily: typography.fontFamily,
              },
              textStyle,
            ],
          },
          title
        )
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  text: {
    fontWeight: '600',
    textAlign: 'center',
  },
});

export function getButtonStyles(variant: ButtonVariant, size: ButtonSize, disabled: boolean) {
  return {
    container: {
      ...sizeStyles[size],
      ...variantStyles[variant],
      minHeight: 44,
      minWidth: 44,
      opacity: disabled ? 0.5 : 1,
    },
    text: {
      color: variantStyles[variant].text,
      fontSize: sizeStyles[size].fontSize,
    },
  };
}
