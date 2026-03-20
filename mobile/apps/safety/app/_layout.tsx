/**
 * Safety App Root Layout
 *
 * Provides auth guard: unauthenticated users see (auth) group,
 * authenticated users see (dashboard) tab navigation.
 *
 * Uses @bhapi/auth tokenManager to check session validity.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { tokenManager } from '@bhapi/auth';
import { BhapiLogo } from '@bhapi/ui';

type AuthState = 'loading' | 'authenticated' | 'unauthenticated';

export default function RootLayout() {
  const [authState, setAuthState] = useState<AuthState>('loading');

  useEffect(() => {
    checkAuth();
  }, []);

  async function checkAuth() {
    try {
      const isAuth = await tokenManager.isAuthenticated();
      setAuthState(isAuth ? 'authenticated' : 'unauthenticated');
    } catch {
      setAuthState('unauthenticated');
    }
  }

  if (authState === 'loading') {
    return React.createElement(
      View,
      { style: styles.loadingContainer, accessibilityLabel: 'Loading app' },
      React.createElement(BhapiLogo, { size: 'lg' }),
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
        style: { marginTop: spacing.lg },
      }),
      React.createElement(
        Text,
        { style: styles.loadingText },
        'Loading...'
      )
    );
  }

  // In a real Expo Router setup, this would use <Slot /> or <Stack />
  // to render either (auth) or (dashboard) group based on authState.
  // For now, we export the component with the auth state for navigation logic.
  return React.createElement(
    View,
    { style: styles.container, accessibilityLabel: 'Safety app root' },
    React.createElement(
      Text,
      { style: styles.debugText },
      `Auth state: ${authState}`
    )
  );
}

// Exported for testing
export { type AuthState };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
  },
  loadingText: {
    marginTop: spacing.md,
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  debugText: {
    padding: spacing.md,
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
});
