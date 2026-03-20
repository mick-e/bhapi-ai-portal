/**
 * Safety App Login Screen
 *
 * Email + password login for parents/guardians.
 * API: POST /api/v1/auth/login { email, password }
 * Response: { access_token, token_type, user }
 *
 * On success, stores token via tokenManager and navigates to dashboard.
 */
import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Button, Input, BhapiLogo } from '@bhapi/ui';
import { tokenManager } from '@bhapi/auth';
import type { LoginRequest, LoginResponse } from '@bhapi/types';

type LoginState = 'idle' | 'loading' | 'error';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginState, setLoginState] = useState<LoginState>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  async function handleLogin() {
    if (!email.trim() || !password.trim()) {
      setErrorMessage('Please enter your email and password.');
      setLoginState('error');
      return;
    }

    setLoginState('loading');
    setErrorMessage('');

    try {
      // API call: POST /api/v1/auth/login
      // In production, use ApiClient from @bhapi/api
      const payload: LoginRequest = { email: email.trim(), password };
      // const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', payload);
      // await tokenManager.setToken(response.access_token);
      // router.replace('/(dashboard)');

      // Placeholder — will be connected to ApiClient in integration
      setLoginState('idle');
    } catch (e: any) {
      setLoginState('error');
      setErrorMessage(e?.message ?? 'Login failed. Please check your credentials.');
    }
  }

  return React.createElement(
    KeyboardAvoidingView,
    {
      style: styles.container,
      behavior: Platform.OS === 'ios' ? 'padding' : 'height',
      accessibilityLabel: 'Login screen',
    },
    React.createElement(
      View,
      { style: styles.logoContainer },
      React.createElement(BhapiLogo, { size: 'lg' })
    ),
    React.createElement(
      Text,
      { style: styles.title, accessibilityRole: 'header' },
      'Welcome Back'
    ),
    React.createElement(
      Text,
      { style: styles.subtitle },
      'Sign in to monitor your family\'s AI safety'
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
    }),
    React.createElement(Input, {
      label: 'Password',
      placeholder: 'Enter your password',
      value: password,
      onChangeText: setPassword,
      secureTextEntry: true,
      autoComplete: 'password',
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
      accessibilityLabel: 'Sign in button',
    }),
    React.createElement(
      TouchableOpacity,
      {
        style: styles.linkContainer,
        accessibilityLabel: 'Sign in with magic link',
        accessibilityRole: 'link',
        // onPress: () => router.push('/(auth)/magic-link'),
      },
      React.createElement(
        Text,
        { style: styles.linkText },
        'Sign in with magic link'
      )
    ),
    React.createElement(
      TouchableOpacity,
      {
        style: styles.linkContainer,
        accessibilityLabel: 'Create an account',
        accessibilityRole: 'link',
        // onPress: () => router.push('/(auth)/register'),
      },
      React.createElement(
        Text,
        { style: styles.linkText },
        'Don\'t have an account? Sign up'
      )
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
