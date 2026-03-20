/**
 * Social App Login Screen (simpler than Safety)
 *
 * Children sign in with a link sent by their parent, or with
 * a simple username/password provided by the parent.
 * API: POST /api/v1/auth/login { email, password }
 */
import React, { useState } from 'react';
import { View, Text, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Button, Input, BhapiLogo } from '@bhapi/ui';
import { tokenManager } from '@bhapi/auth';

type LoginState = 'idle' | 'loading' | 'error';

export default function SocialLoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginState, setLoginState] = useState<LoginState>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  async function handleLogin() {
    if (!email.trim() || !password.trim()) {
      setErrorMessage('Please fill in all fields.');
      setLoginState('error');
      return;
    }

    setLoginState('loading');
    setErrorMessage('');

    try {
      // API call: POST /api/v1/auth/login
      // const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', {
      //   email: email.trim(),
      //   password,
      // });
      // await tokenManager.setToken(response.access_token);
      // router.replace('/(feed)');
      setLoginState('idle');
    } catch (e: any) {
      setLoginState('error');
      setErrorMessage(e?.message ?? 'Could not sign in. Ask your parent for help.');
    }
  }

  return React.createElement(
    KeyboardAvoidingView,
    {
      style: styles.container,
      behavior: Platform.OS === 'ios' ? 'padding' : 'height',
      accessibilityLabel: 'Login',
    },
    React.createElement(
      View,
      { style: styles.logoContainer },
      React.createElement(BhapiLogo, { size: 'lg' })
    ),
    React.createElement(
      Text,
      { style: styles.title, accessibilityRole: 'header' },
      'Hey there!'
    ),
    React.createElement(
      Text,
      { style: styles.subtitle },
      'Sign in to see what\'s new'
    ),
    React.createElement(Input, {
      label: 'Username or Email',
      placeholder: 'Your username',
      value: email,
      onChangeText: setEmail,
      autoCapitalize: 'none',
      accessibilityLabel: 'Username or email',
    }),
    React.createElement(Input, {
      label: 'Password',
      placeholder: 'Your password',
      value: password,
      onChangeText: setPassword,
      secureTextEntry: true,
      accessibilityLabel: 'Password',
    }),
    errorMessage
      ? React.createElement(
          Text,
          { style: styles.errorText, accessibilityRole: 'alert' },
          errorMessage
        )
      : null,
    React.createElement(Button, {
      title: 'Sign In',
      onPress: handleLogin,
      isLoading: loginState === 'loading',
      disabled: loginState === 'loading',
      style: styles.loginButton,
      accessibilityLabel: 'Sign in',
    }),
    React.createElement(
      Text,
      { style: styles.helpText },
      'Need help signing in? Ask your parent!'
    )
  );
}

// Exported for testing
export { type LoginState };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
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
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  loginButton: {
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
