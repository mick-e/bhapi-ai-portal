/**
 * Safety App Registration Screen
 *
 * Parent/guardian registration with privacy_notice_accepted.
 * API: POST /api/v1/auth/register {
 *   email, password, name, privacy_notice_accepted: true
 * }
 *
 * IMPORTANT: privacy_notice_accepted must be true or backend returns 422.
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Button, Input, BhapiLogo } from '@bhapi/ui';

type RegisterState = 'idle' | 'loading' | 'success' | 'error';

export default function RegisterScreen() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [registerState, setRegisterState] = useState<RegisterState>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  function validate(): string | null {
    if (!name.trim()) return 'Please enter your name.';
    if (!email.trim()) return 'Please enter your email address.';
    if (password.length < 8) return 'Password must be at least 8 characters.';
    if (password !== confirmPassword) return 'Passwords do not match.';
    if (!privacyAccepted) return 'You must accept the privacy notice to continue.';
    return null;
  }

  async function handleRegister() {
    const validationError = validate();
    if (validationError) {
      setErrorMessage(validationError);
      setRegisterState('error');
      return;
    }

    setRegisterState('loading');
    setErrorMessage('');

    try {
      // API call: POST /api/v1/auth/register
      // const response = await apiClient.post('/api/v1/auth/register', {
      //   name: name.trim(),
      //   email: email.trim(),
      //   password,
      //   privacy_notice_accepted: true,
      // });
      // await tokenManager.setToken(response.access_token);
      // router.replace('/(dashboard)');

      setRegisterState('success');
    } catch (e: any) {
      setRegisterState('error');
      setErrorMessage(e?.message ?? 'Registration failed. Please try again.');
    }
  }

  if (registerState === 'success') {
    return React.createElement(
      View,
      { style: styles.successContainer, accessibilityLabel: 'Registration successful' },
      React.createElement(
        Text,
        { style: styles.successTitle },
        'Account Created!'
      ),
      React.createElement(
        Text,
        { style: styles.successText },
        'Please check your email to verify your account.'
      )
    );
  }

  return React.createElement(
    KeyboardAvoidingView,
    {
      style: { flex: 1 },
      behavior: Platform.OS === 'ios' ? 'padding' : 'height',
    },
    React.createElement(
      ScrollView,
      {
        contentContainerStyle: styles.container,
        keyboardShouldPersistTaps: 'handled',
        accessibilityLabel: 'Registration screen',
      },
      React.createElement(
        View,
        { style: styles.logoContainer },
        React.createElement(BhapiLogo, { size: 'md' })
      ),
      React.createElement(
        Text,
        { style: styles.title, accessibilityRole: 'header' },
        'Create Your Account'
      ),
      React.createElement(
        Text,
        { style: styles.subtitle },
        'Start monitoring your family\'s AI safety'
      ),
      React.createElement(Input, {
        label: 'Full Name',
        placeholder: 'Your name',
        value: name,
        onChangeText: setName,
        autoComplete: 'name',
        accessibilityLabel: 'Full name',
      }),
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
        placeholder: 'At least 8 characters',
        value: password,
        onChangeText: setPassword,
        secureTextEntry: true,
        accessibilityLabel: 'Password',
      }),
      React.createElement(Input, {
        label: 'Confirm Password',
        placeholder: 'Re-enter your password',
        value: confirmPassword,
        onChangeText: setConfirmPassword,
        secureTextEntry: true,
        accessibilityLabel: 'Confirm password',
      }),
      // Privacy notice checkbox
      React.createElement(
        TouchableOpacity,
        {
          style: styles.checkboxRow,
          onPress: () => setPrivacyAccepted(!privacyAccepted),
          accessibilityRole: 'checkbox',
          accessibilityState: { checked: privacyAccepted },
          accessibilityLabel: 'Accept privacy notice',
        },
        React.createElement(
          View,
          {
            style: [
              styles.checkbox,
              privacyAccepted ? styles.checkboxChecked : null,
            ],
          },
          privacyAccepted
            ? React.createElement(Text, { style: styles.checkmark }, '\u2713')
            : null
        ),
        React.createElement(
          Text,
          { style: styles.checkboxLabel },
          'I have read and accept the Privacy Notice and Terms of Service'
        )
      ),
      errorMessage
        ? React.createElement(
            Text,
            { style: styles.errorText, accessibilityRole: 'alert' },
            errorMessage
          )
        : null,
      React.createElement(Button, {
        title: 'Create Account',
        onPress: handleRegister,
        isLoading: registerState === 'loading',
        disabled: registerState === 'loading',
        style: styles.registerButton,
        accessibilityLabel: 'Create account button',
      }),
      React.createElement(
        TouchableOpacity,
        {
          style: styles.linkContainer,
          accessibilityLabel: 'Go to login',
          accessibilityRole: 'link',
          // onPress: () => router.push('/(auth)/login'),
        },
        React.createElement(
          Text,
          { style: styles.linkText },
          'Already have an account? Sign in'
        )
      )
    )
  );
}

// Exported for testing
export { type RegisterState };

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.xl,
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
  subtitle: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    textAlign: 'center',
    marginBottom: spacing.xl,
    fontFamily: typography.fontFamily,
  },
  checkboxRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: spacing.md,
    minHeight: 44,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderWidth: 2,
    borderColor: colors.neutral[200],
    borderRadius: 4,
    marginRight: spacing.sm,
    marginTop: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkboxChecked: {
    backgroundColor: colors.primary[600],
    borderColor: colors.primary[600],
  },
  checkmark: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
  checkboxLabel: {
    flex: 1,
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
    lineHeight: 20,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  registerButton: {
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
  successContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    backgroundColor: '#FFFFFF',
  },
  successTitle: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.semantic.success,
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  successText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    textAlign: 'center',
    fontFamily: typography.fontFamily,
  },
});
