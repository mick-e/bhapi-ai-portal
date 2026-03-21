/**
 * Age Verification Screen — Yoti WebView integration
 *
 * Initiates a Yoti age verification session, renders the Yoti flow in a
 * WebView, handles the callback, and routes the user to the next onboarding
 * step (parent consent if <13, profile creation otherwise).
 *
 * API: POST /api/v1/integrations/age-verify/start → { session_id, url }
 *      GET  /api/v1/integrations/age-verify/{session_id}/result → YotiVerificationResult
 */
import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Button, BhapiLogo } from '@bhapi/ui';

type VerifyState = 'idle' | 'loading' | 'verifying' | 'success' | 'error';

export interface AgeVerifyResult {
  verified: boolean;
  age_estimate: number | null;
  session_id: string;
}

interface AgeVerifyScreenProps {
  onVerified?: (result: AgeVerifyResult) => void;
  onSkip?: () => void;
}

export default function AgeVerifyScreen(props: AgeVerifyScreenProps) {
  const { onVerified, onSkip } = props;
  const [state, setState] = useState<VerifyState>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [result, setResult] = useState<AgeVerifyResult | null>(null);

  const startVerification = useCallback(async () => {
    setState('loading');
    setErrorMessage('');

    try {
      // API call: POST /api/v1/integrations/age-verify/start
      // In production this would open a Yoti WebView session.
      // const session = await apiClient.post('/api/v1/integrations/age-verify/start', {});
      // For now, simulate the flow:
      setState('verifying');

      // Simulate Yoti callback after WebView completes
      // In production: listen for navigation to callback URL
      // const verifyResult = await apiClient.get(`/api/v1/integrations/age-verify/${session.session_id}/result`);

      // Placeholder: verification is handled by parent component
      setState('idle');
    } catch (e: any) {
      setState('error');
      setErrorMessage(e?.message ?? 'Verification failed. Please try again.');
    }
  }, []);

  const handleVerificationComplete = useCallback(
    (verifyResult: AgeVerifyResult) => {
      setResult(verifyResult);
      setState('success');
      if (onVerified) {
        onVerified(verifyResult);
      }
    },
    [onVerified],
  );

  return React.createElement(
    View,
    { style: styles.container, accessibilityLabel: 'Age Verification' },

    // Logo
    React.createElement(
      View,
      { style: styles.logoContainer },
      React.createElement(BhapiLogo, { size: 'md' }),
    ),

    // Title
    React.createElement(
      Text,
      { style: styles.title, accessibilityRole: 'header' },
      'Verify Your Age',
    ),

    // Description
    React.createElement(
      Text,
      { style: styles.description },
      'We need to check your age to keep everyone safe. ' +
        'Your parent may need to help with this step.',
    ),

    // Loading state
    state === 'loading' || state === 'verifying'
      ? React.createElement(
          View,
          { style: styles.loadingContainer },
          React.createElement(ActivityIndicator, {
            size: 'large',
            color: colors.brand?.primary ?? '#FF6B35',
          }),
          React.createElement(
            Text,
            { style: styles.loadingText },
            state === 'loading'
              ? 'Starting verification...'
              : 'Checking your age...',
          ),
        )
      : null,

    // Success state
    state === 'success' && result
      ? React.createElement(
          View,
          { style: styles.resultContainer, accessibilityRole: 'alert' },
          React.createElement(
            Text,
            { style: styles.successText },
            result.verified
              ? 'Age verified!'
              : 'Could not verify your age.',
          ),
          result.age_estimate !== null
            ? React.createElement(
                Text,
                { style: styles.ageText },
                `Age: ${result.age_estimate}`,
              )
            : null,
          result.verified && result.age_estimate !== null && result.age_estimate < 13
            ? React.createElement(
                Text,
                { style: styles.consentNote },
                'A parent or guardian will need to give permission for you to continue.',
              )
            : null,
        )
      : null,

    // Error state
    state === 'error'
      ? React.createElement(
          Text,
          { style: styles.errorText, accessibilityRole: 'alert' },
          errorMessage,
        )
      : null,

    // Start button (only when idle or error)
    state === 'idle' || state === 'error'
      ? React.createElement(Button, {
          title: 'Start Age Check',
          onPress: startVerification,
          style: styles.verifyButton,
          accessibilityLabel: 'Start age verification',
        })
      : null,

    // Help text
    React.createElement(
      Text,
      { style: styles.helpText },
      'Ask a parent or guardian if you need help.',
    ),
  );
}

// Exported for testing
export { type VerifyState };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    backgroundColor: '#FFFFFF',
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  title: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    textAlign: 'center',
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  description: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    textAlign: 'center',
    marginBottom: spacing.xl,
    lineHeight: 22,
    fontFamily: typography.fontFamily,
  },
  loadingContainer: {
    alignItems: 'center',
    marginVertical: spacing.lg,
  },
  loadingText: {
    marginTop: spacing.md,
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  resultContainer: {
    alignItems: 'center',
    marginVertical: spacing.lg,
    padding: spacing.lg,
    borderRadius: 12,
    backgroundColor: colors.neutral[50],
  },
  successText: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.semantic?.success ?? '#16A34A',
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  ageText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  consentNote: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    textAlign: 'center',
    fontFamily: typography.fontFamily,
  },
  errorText: {
    color: colors.semantic?.error ?? '#DC2626',
    fontSize: typography.sizes.sm,
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  verifyButton: {
    marginTop: spacing.md,
    marginBottom: spacing.lg,
  },
  helpText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    textAlign: 'center',
    fontFamily: typography.fontFamily,
  },
});
