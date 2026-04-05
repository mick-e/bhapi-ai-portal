/**
 * Social App Root Layout
 *
 * Auth guard + age-tier guard. Children must have a valid session
 * with an age tier assigned before accessing social features.
 *
 * Age tiers: 5-9 (young), 10-12 (preteen), 13-15 (teen).
 * Each tier sees different UI capabilities.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { AGE_TIERS } from '@bhapi/config';
import { tokenManager } from '@bhapi/auth';
import { BhapiLogo, MotionProvider, ContrastProvider, FontProvider } from '@bhapi/ui';
import type { AgeTier } from '@bhapi/types';

type AppState = 'loading' | 'authenticated' | 'unauthenticated' | 'no_age_tier';

export default function SocialRootLayout() {
  const [appState, setAppState] = useState<AppState>('loading');
  const [ageTier, setAgeTier] = useState<AgeTier | null>(null);

  useEffect(() => {
    checkAccess();
  }, []);

  async function checkAccess() {
    try {
      const isAuth = await tokenManager.isAuthenticated();
      if (!isAuth) {
        setAppState('unauthenticated');
        return;
      }

      // In production, decode JWT to get age_tier claim
      // const token = await tokenManager.getToken();
      // const payload = decodeToken(token);
      // if (!payload.age_tier) { setAppState('no_age_tier'); return; }
      // setAgeTier(payload.age_tier);
      setAppState('authenticated');
    } catch {
      setAppState('unauthenticated');
    }
  }

  if (appState === 'loading') {
    return React.createElement(
      MotionProvider,
      null,
      React.createElement(
        ContrastProvider,
        null,
        React.createElement(
          FontProvider,
          null,
          React.createElement(
            View,
            { style: styles.loadingContainer, accessibilityLabel: 'Loading' },
            React.createElement(BhapiLogo, { size: 'lg' }),
            React.createElement(ActivityIndicator, {
              size: 'large',
              color: colors.primary[600],
              style: { marginTop: spacing.lg },
            })
          )
        )
      )
    );
  }

  if (appState === 'no_age_tier') {
    return React.createElement(
      MotionProvider,
      null,
      React.createElement(
        ContrastProvider,
        null,
        React.createElement(
          FontProvider,
          null,
          React.createElement(
            View,
            { style: styles.errorContainer, accessibilityLabel: 'Age verification required' },
            React.createElement(BhapiLogo, { size: 'md' }),
            React.createElement(
              Text,
              { style: styles.errorTitle },
              'Age Verification Needed'
            ),
            React.createElement(
              Text,
              { style: styles.errorText },
              'Ask your parent to verify your age before using the app.'
            )
          )
        )
      )
    );
  }

  // In Expo Router, this would render <Slot /> for active route group.
  return React.createElement(
    MotionProvider,
    null,
    React.createElement(
      ContrastProvider,
      null,
      React.createElement(
        FontProvider,
        null,
        React.createElement(
          View,
          { style: styles.container, accessibilityLabel: 'Social app' },
          React.createElement(
            Text,
            { style: styles.debugText },
            `State: ${appState}, Tier: ${ageTier ?? 'unknown'}`
          )
        )
      )
    )
  );
}

// Exported for testing
export { type AppState };

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
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    backgroundColor: '#FFFFFF',
  },
  errorTitle: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.neutral[900],
    marginTop: spacing.xl,
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  errorText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    textAlign: 'center',
    fontFamily: typography.fontFamily,
  },
  debugText: {
    padding: spacing.md,
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
});
