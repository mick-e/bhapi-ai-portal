import React from 'react';
import { View, Text, TextInput, StyleSheet, TextInputProps, ViewStyle } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

export interface InputProps extends Omit<TextInputProps, 'style'> {
  label?: string;
  error?: string;
  style?: ViewStyle;
  inputStyle?: ViewStyle;
  accessibilityLabel?: string;
}

export function Input({
  label,
  error,
  style,
  inputStyle,
  accessibilityLabel,
  secureTextEntry,
  placeholder,
  value,
  onChangeText,
  ...rest
}: InputProps) {
  return React.createElement(
    View,
    { style: [styles.container, style] },
    label
      ? React.createElement(
          Text,
          { style: styles.label },
          label
        )
      : null,
    React.createElement(TextInput, {
      style: [
        styles.input,
        error ? styles.inputError : null,
        inputStyle,
      ],
      placeholder,
      placeholderTextColor: colors.neutral[500],
      value,
      onChangeText,
      secureTextEntry,
      accessibilityLabel: accessibilityLabel ?? label ?? placeholder,
      ...rest,
    }),
    error
      ? React.createElement(
          Text,
          { style: styles.errorText, accessibilityRole: 'alert' },
          error
        )
      : null
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: spacing.md,
  },
  label: {
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    color: colors.neutral[700],
    marginBottom: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  input: {
    height: 48,
    minHeight: 44, // WCAG 2.1 AA
    borderWidth: 1,
    borderColor: colors.neutral[200],
    borderRadius: 8,
    paddingHorizontal: spacing.md,
    fontSize: typography.sizes.base,
    color: colors.neutral[900],
    backgroundColor: '#FFFFFF',
    fontFamily: typography.fontFamily,
  },
  inputError: {
    borderColor: colors.semantic.error,
    borderWidth: 2,
  },
  errorText: {
    fontSize: typography.sizes.xs,
    color: colors.semantic.error,
    marginTop: spacing.xs,
    fontFamily: typography.fontFamily,
  },
});

export const inputStyles = {
  height: 48,
  minHeight: 44,
  borderRadius: 8,
  errorBorderColor: colors.semantic.error,
};
