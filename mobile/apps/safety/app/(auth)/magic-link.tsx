/**
 * Magic Link Login Screen
 *
 * Email entry -> sends magic link -> shows "check your email" state.
 * API: POST /api/v1/auth/magic-link { email }
 */
import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Button, Input, BhapiLogo } from '@bhapi/ui';

type MagicLinkState = 'input' | 'sending' | 'sent' | 'error';

export default function MagicLinkScreen() {
  const [email, setEmail] = useState('');
  const [state, setState] = useState<MagicLinkState>('input');
  const [errorMessage, setErrorMessage] = useState('');

  async function handleSendLink() {
    if (!email.trim()) {
      setErrorMessage('Please enter your email address.');
      setState('error');
      return;
    }

    setState('sending');
    setErrorMessage('');

    try {
      // API call: POST /api/v1/auth/magic-link
      // await apiClient.post('/api/v1/auth/magic-link', { email: email.trim() });
      setState('sent');
    } catch (e: any) {
      setState('error');
      setErrorMessage(e?.message ?? 'Failed to send magic link. Please try again.');
    }
  }

  // "Check your email" confirmation state
  if (state === 'sent') {
    return React.createElement(
      View,
      { style: styles.centeredContainer, accessibilityLabel: 'Magic link sent' },
      React.createElement(BhapiLogo, { size: 'md' }),
      React.createElement(
        Text,
        { style: styles.sentTitle },
        'Check Your Email'
      ),
      React.createElement(
        Text,
        { style: styles.sentText },
        `We sent a sign-in link to ${email}. Tap the link in the email to sign in.`
      ),
      React.createElement(
        Text,
        { style: styles.sentHint },
        'Don\'t see it? Check your spam folder.'
      ),
      React.createElement(Button, {
        title: 'Resend Link',
        onPress: handleSendLink,
        variant: 'outline',
        style: styles.resendButton,
        accessibilityLabel: 'Resend magic link',
      }),
      React.createElement(
        TouchableOpacity,
        {
          style: styles.linkContainer,
          onPress: () => {
            setState('input');
            setEmail('');
          },
          accessibilityLabel: 'Try a different email',
          accessibilityRole: 'link',
        },
        React.createElement(
          Text,
          { style: styles.linkText },
          'Try a different email'
        )
      )
    );
  }

  // Email input state
  return React.createElement(
    KeyboardAvoidingView,
    {
      style: styles.container,
      behavior: Platform.OS === 'ios' ? 'padding' : 'height',
      accessibilityLabel: 'Magic link login',
    },
    React.createElement(
      View,
      { style: styles.logoContainer },
      React.createElement(BhapiLogo, { size: 'lg' })
    ),
    React.createElement(
      Text,
      { style: styles.title, accessibilityRole: 'header' },
      'Sign In with Email'
    ),
    React.createElement(
      Text,
      { style: styles.subtitle },
      'We\'ll send you a secure sign-in link'
    ),
    React.createElement(Input, {
      label: 'Email',
      placeholder: 'parent@example.com',
      value: email,
      onChangeText: setEmail,
      keyboardType: 'email-address',
      autoCapitalize: 'none',
      autoComplete: 'email',
      accessibilityLabel: 'Email address',
      error: state === 'error' ? errorMessage : undefined,
    }),
    React.createElement(Button, {
      title: 'Send Sign-In Link',
      onPress: handleSendLink,
      isLoading: state === 'sending',
      disabled: state === 'sending',
      style: styles.sendButton,
      accessibilityLabel: 'Send sign-in link',
    }),
    React.createElement(
      TouchableOpacity,
      {
        style: styles.linkContainer,
        accessibilityLabel: 'Sign in with password',
        accessibilityRole: 'link',
        // onPress: () => router.push('/(auth)/login'),
      },
      React.createElement(
        Text,
        { style: styles.linkText },
        'Sign in with password instead'
      )
    )
  );
}

// Exported for testing
export { type MagicLinkState };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    backgroundColor: '#FFFFFF',
  },
  centeredContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    backgroundColor: '#FFFFFF',
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: spacing.xl,
  },
  title: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    textAlign: 'center',
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  subtitle: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    textAlign: 'center',
    marginBottom: spacing.xl,
    fontFamily: typography.fontFamily,
  },
  sentTitle: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    marginTop: spacing.xl,
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  sentText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
    lineHeight: 24,
  },
  sentHint: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    textAlign: 'center',
    marginBottom: spacing.xl,
    fontFamily: typography.fontFamily,
  },
  sendButton: {
    marginTop: spacing.md,
    marginBottom: spacing.lg,
  },
  resendButton: {
    marginBottom: spacing.md,
    minWidth: 160,
  },
  linkContainer: {
    alignItems: 'center',
    paddingVertical: spacing.sm,
    minHeight: 44,
    justifyContent: 'center',
  },
  linkText: {
    color: colors.primary[700],
    fontSize: typography.sizes.base,
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
});
