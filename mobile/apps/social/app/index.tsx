/**
 * Social App entry point.
 *
 * Redirects to login or feed based on authentication state.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { tokenManager } from '@bhapi/auth';
import { BhapiLogo } from '@bhapi/ui';

export default function SocialIndex() {
  const [checking, setChecking] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    async function check() {
      try {
        const auth = await tokenManager.isAuthenticated();
        setIsAuthenticated(auth);
      } catch {
        setIsAuthenticated(false);
      } finally {
        setChecking(false);
      }
    }
    check();
  }, []);

  if (checking) {
    return React.createElement(
      View,
      { style: styles.container, accessibilityLabel: 'Loading' },
      React.createElement(BhapiLogo, { size: 'lg' }),
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
        style: { marginTop: spacing.lg },
      })
    );
  }

  return React.createElement(
    View,
    { style: styles.container, accessibilityLabel: 'Social app' },
    React.createElement(
      Text,
      { style: styles.redirectText },
      isAuthenticated ? 'Redirecting to feed...' : 'Redirecting to login...'
    )
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
  },
  redirectText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
});
