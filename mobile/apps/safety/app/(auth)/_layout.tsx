/**
 * Auth Layout — No tabs, centered content.
 *
 * Wraps login, register, and magic-link screens with
 * consistent padding, safe area, and branding.
 */
import React from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import { colors, spacing } from '@bhapi/config';
import { BhapiLogo } from '@bhapi/ui';

export default function AuthLayout() {
  // In Expo Router, this would render <Slot /> for the active auth screen.
  return React.createElement(
    ScrollView,
    {
      style: styles.scrollView,
      contentContainerStyle: styles.container,
      keyboardShouldPersistTaps: 'handled',
      accessibilityLabel: 'Authentication',
    },
    React.createElement(
      View,
      { style: styles.logoContainer },
      React.createElement(BhapiLogo, { size: 'lg' })
    ),
    React.createElement(View, { style: styles.content })
    // <Slot /> would render here in Expo Router
  );
}

const styles = StyleSheet.create({
  scrollView: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  container: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.xl,
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: spacing['2xl'],
  },
  content: {
    width: '100%',
    maxWidth: 400,
    alignSelf: 'center',
  },
});
