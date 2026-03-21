/**
 * Trusted Adult Request Screen
 *
 * A private, child-friendly screen where children can request help from
 * a trusted adult. Key design principles:
 *
 * 1. Reassuring tone: "You are not in trouble"
 * 2. Private: "This is private. Your parent will NOT see this."
 * 3. Provides helpline numbers alongside the form
 * 4. Simple, accessible language appropriate for ages 5-15
 *
 * API: POST /api/v1/moderation/trusted-adult (not implemented yet — uses placeholder)
 */
import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Linking,
  Alert,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Card } from '@bhapi/ui';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Helpline {
  name: string;
  number: string;
  available: string;
}

type ScreenState = 'form' | 'submitting' | 'submitted';

// ---------------------------------------------------------------------------
// Helplines (shown regardless of form submission)
// ---------------------------------------------------------------------------

const HELPLINES: Helpline[] = [
  { name: 'Childhelp National Child Abuse Hotline', number: '1-800-422-4453', available: '24/7' },
  { name: 'Crisis Text Line', number: 'Text HOME to 741741', available: '24/7' },
  { name: 'National Domestic Violence Hotline', number: '1-800-799-7233', available: '24/7' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function TrustedAdultScreen() {
  const [screenState, setScreenState] = useState<ScreenState>('form');
  const [adultName, setAdultName] = useState('');
  const [adultContact, setAdultContact] = useState('');
  const [reason, setReason] = useState('');

  const handleSubmit = useCallback(async () => {
    setScreenState('submitting');
    try {
      // In production, this would call the API:
      // POST /api/v1/moderation/trusted-adult
      // For now, simulate a brief delay
      await new Promise((resolve) => setTimeout(resolve, 800));
      setScreenState('submitted');
    } catch {
      Alert.alert(
        'Something went wrong',
        'Please try again or call one of the helplines below.',
      );
      setScreenState('form');
    }
  }, [adultName, adultContact, reason]);

  const handleCallHelpline = useCallback((number: string) => {
    // Only dial if it's a phone number (not text-based)
    if (number.startsWith('1-') || number.startsWith('0')) {
      const cleanNumber = number.replace(/[^0-9+]/g, '');
      Linking.openURL(`tel:${cleanNumber}`).catch(() => {
        Alert.alert('Unable to make a call', `Please dial ${number} from your phone.`);
      });
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Submitted confirmation
  // ---------------------------------------------------------------------------

  if (screenState === 'submitted') {
    return React.createElement(
      ScrollView,
      { style: styles.screen, contentContainerStyle: styles.content },
      React.createElement(
        View,
        { style: styles.successContainer },
        React.createElement(
          Text,
          { style: styles.successIcon, accessibilityLabel: 'Checkmark' },
          '\u{2705}'
        ),
        React.createElement(
          Text,
          { style: styles.successTitle },
          'Your request has been sent'
        ),
        React.createElement(
          Text,
          { style: styles.successMessage },
          'This is private. Your parent or guardian will NOT see this request. ' +
          'Someone from our team will help connect you with a trusted adult.'
        ),
        React.createElement(
          Text,
          { style: styles.successReminder },
          'If you are in immediate danger, please call one of the helplines below.'
        )
      ),
      // Always show helplines
      renderHelplines(HELPLINES, handleCallHelpline)
    );
  }

  // ---------------------------------------------------------------------------
  // Main form
  // ---------------------------------------------------------------------------

  return React.createElement(
    ScrollView,
    { style: styles.screen, contentContainerStyle: styles.content },
    // Privacy banner
    React.createElement(
      View,
      {
        style: styles.privacyBanner,
        accessibilityRole: 'alert',
      },
      React.createElement(
        Text,
        { style: styles.privacyIcon },
        '\u{1F512}' // Lock emoji
      ),
      React.createElement(
        Text,
        { style: styles.privacyText },
        'This is private. Your parent or guardian will NOT see this.'
      )
    ),

    // Reassuring header
    React.createElement(
      Text,
      { style: styles.title },
      'Need to talk to someone you trust?'
    ),
    React.createElement(
      Text,
      { style: styles.subtitle },
      'You are not in trouble. We want to help you feel safe. ' +
      'You can tell us about a trusted adult you would like to talk to, ' +
      'or you can call one of the helplines below.'
    ),

    // Form card
    React.createElement(
      Card,
      { style: styles.formCard },
      React.createElement(
        Text,
        { style: styles.label },
        'Name of a trusted adult (optional)'
      ),
      React.createElement(TextInput, {
        style: styles.input,
        value: adultName,
        onChangeText: setAdultName,
        placeholder: 'e.g. Aunt Jane, Coach Mike, Teacher Ms. Lee',
        placeholderTextColor: '#9CA3AF',
        accessibilityLabel: 'Name of trusted adult',
      }),

      React.createElement(
        Text,
        { style: styles.label },
        'How can we reach them? (optional)'
      ),
      React.createElement(TextInput, {
        style: styles.input,
        value: adultContact,
        onChangeText: setAdultContact,
        placeholder: 'Phone number or email',
        placeholderTextColor: '#9CA3AF',
        accessibilityLabel: 'Contact information for trusted adult',
      }),

      React.createElement(
        Text,
        { style: styles.label },
        'What is happening? (optional)'
      ),
      React.createElement(TextInput, {
        style: [styles.input, styles.textArea],
        value: reason,
        onChangeText: setReason,
        placeholder: 'You can share as much or as little as you want.',
        placeholderTextColor: '#9CA3AF',
        multiline: true,
        numberOfLines: 4,
        textAlignVertical: 'top',
        accessibilityLabel: 'What is happening',
      }),

      React.createElement(
        TouchableOpacity,
        {
          style: [styles.submitButton, screenState === 'submitting' && styles.disabled],
          onPress: handleSubmit,
          disabled: screenState === 'submitting',
          accessibilityRole: 'button',
          accessibilityLabel: 'Send my request',
        },
        screenState === 'submitting'
          ? React.createElement(ActivityIndicator, { color: '#FFFFFF', size: 'small' })
          : React.createElement(
              Text,
              { style: styles.submitText },
              'Send my request'
            )
      )
    ),

    // Helplines section
    React.createElement(
      Text,
      { style: styles.helplineHeader },
      'You can also call for help right now'
    ),
    renderHelplines(HELPLINES, handleCallHelpline)
  );
}

// ---------------------------------------------------------------------------
// Helpline rendering
// ---------------------------------------------------------------------------

function renderHelplines(
  helplines: Helpline[],
  onCall: (number: string) => void,
) {
  return React.createElement(
    View,
    { style: styles.helplineContainer },
    ...helplines.map((hl, idx) =>
      React.createElement(
        TouchableOpacity,
        {
          key: `helpline-${idx}`,
          style: styles.helplineCard,
          onPress: () => onCall(hl.number),
          accessibilityRole: 'button',
          accessibilityLabel: `Call ${hl.name} at ${hl.number}`,
        },
        React.createElement(
          Text,
          { style: styles.helplineName },
          hl.name
        ),
        React.createElement(
          Text,
          { style: styles.helplineNumber },
          hl.number
        ),
        React.createElement(
          Text,
          { style: styles.helplineAvailable },
          `Available ${hl.available}`
        )
      )
    )
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  content: {
    padding: spacing.lg,
    paddingBottom: spacing.xl * 2,
  },
  privacyBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#EFF6FF', // Soft blue — calming, not alarming
    borderRadius: 8,
    padding: spacing.md,
    marginBottom: spacing.lg,
    borderWidth: 1,
    borderColor: '#BFDBFE',
  },
  privacyIcon: {
    fontSize: typography.sizes.lg,
    marginRight: spacing.sm,
  },
  privacyText: {
    flex: 1,
    fontSize: typography.sizes.sm,
    color: '#1E40AF',
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  title: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: '#111827',
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  subtitle: {
    fontSize: typography.sizes.base,
    color: '#6B7280',
    lineHeight: 22,
    marginBottom: spacing.lg,
    fontFamily: typography.fontFamily,
  },
  formCard: {
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  label: {
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    color: '#374151',
    marginBottom: spacing.xs,
    marginTop: spacing.md,
    fontFamily: typography.fontFamily,
  },
  input: {
    borderWidth: 1,
    borderColor: '#D1D5DB',
    borderRadius: 8,
    padding: spacing.sm,
    fontSize: typography.sizes.base,
    color: '#111827',
    minHeight: 44,
    fontFamily: typography.fontFamily,
  },
  textArea: {
    minHeight: 100,
  },
  submitButton: {
    backgroundColor: colors.accent[500], // Teal — calming, not alarming
    borderRadius: 8,
    paddingVertical: spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: spacing.lg,
    minHeight: 48,
  },
  disabled: {
    opacity: 0.6,
  },
  submitText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  helplineHeader: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: '#111827',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  helplineContainer: {
    gap: spacing.sm,
  },
  helplineCard: {
    backgroundColor: '#FFF7ED', // Warm orange tint
    borderRadius: 8,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: '#FED7AA',
    minHeight: 44,
  },
  helplineName: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: '#9A3412',
    fontFamily: typography.fontFamily,
  },
  helplineNumber: {
    fontSize: typography.sizes.lg,
    fontWeight: '700',
    color: '#C2410C',
    marginTop: 2,
    fontFamily: typography.fontFamily,
  },
  helplineAvailable: {
    fontSize: typography.sizes.xs,
    color: '#9A3412',
    marginTop: 2,
    fontFamily: typography.fontFamily,
  },
  // Success screen
  successContainer: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
  },
  successIcon: {
    fontSize: 48,
    marginBottom: spacing.md,
  },
  successTitle: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: '#111827',
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  successMessage: {
    fontSize: typography.sizes.base,
    color: '#6B7280',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  successReminder: {
    fontSize: typography.sizes.sm,
    color: '#DC2626',
    fontWeight: '600',
    textAlign: 'center',
    fontFamily: typography.fontFamily,
  },
});
