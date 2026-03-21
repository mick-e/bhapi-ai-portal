/**
 * Social Onboarding Wizard — multi-step flow
 *
 * Steps:
 *   1. Age Verification (Yoti)
 *   2. Parent Consent (required for <13)
 *   3. Profile Creation (display name + avatar + bio)
 *   4. Tier Assignment Confirmation
 *
 * API:
 *   POST /api/v1/integrations/age-verify/start
 *   GET  /api/v1/integrations/age-verify/{session_id}/result
 *   POST /api/v1/social/profiles { display_name, bio?, avatar_url?, date_of_birth }
 *   GET  /api/v1/age-tier/me
 */
import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Button, Input, BhapiLogo } from '@bhapi/ui';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type OnboardingStep =
  | 'age_verify'
  | 'parent_consent'
  | 'profile_create'
  | 'complete';

export interface OnboardingState {
  step: OnboardingStep;
  age_verified: boolean;
  age_estimate: number | null;
  parent_consent_given: boolean;
  profile_created: boolean;
}

interface OnboardingScreenProps {
  onComplete?: () => void;
  initialStep?: OnboardingStep;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MIN_AGE = 5;
const MAX_AGE = 15;
const CONSENT_AGE_THRESHOLD = 13;
const MIN_DISPLAY_NAME_LENGTH = 2;
const MAX_DISPLAY_NAME_LENGTH = 30;
const MAX_BIO_LENGTH = 150;

// Tier labels for the confirmation screen
const TIER_LABELS: Record<string, string> = {
  young: 'Explorer (5-9)',
  preteen: 'Creator (10-12)',
  teen: 'Trailblazer (13-15)',
};

function getTierForAge(age: number): string | null {
  if (age >= 5 && age <= 9) return 'young';
  if (age >= 10 && age <= 12) return 'preteen';
  if (age >= 13 && age <= 15) return 'teen';
  return null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function OnboardingScreen(props: OnboardingScreenProps) {
  const { onComplete, initialStep = 'age_verify' } = props;

  const [state, setState] = useState<OnboardingState>({
    step: initialStep,
    age_verified: false,
    age_estimate: null,
    parent_consent_given: false,
    profile_created: false,
  });

  const [displayName, setDisplayName] = useState('');
  const [bio, setBio] = useState('');
  const [parentEmail, setParentEmail] = useState('');
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // --- Step 1: Age Verification ---

  const handleAgeVerified = useCallback(
    (age: number) => {
      const needsConsent = age < CONSENT_AGE_THRESHOLD;
      setState((prev) => ({
        ...prev,
        age_verified: true,
        age_estimate: age,
        step: needsConsent ? 'parent_consent' : 'profile_create',
      }));
    },
    [],
  );

  const handleStartVerification = useCallback(async () => {
    setIsSubmitting(true);
    setFormError('');
    try {
      // In production: POST /api/v1/integrations/age-verify/start
      // Then open WebView and await callback result.
      // For now, this is wired up but the actual Yoti WebView
      // integration happens in age-verify.tsx.
      setIsSubmitting(false);
    } catch (e: any) {
      setFormError(e?.message ?? 'Verification failed.');
      setIsSubmitting(false);
    }
  }, []);

  // --- Step 2: Parent Consent ---

  const handleRequestConsent = useCallback(async () => {
    if (!parentEmail.trim() || !parentEmail.includes('@')) {
      setFormError('Please enter a valid parent email address.');
      return;
    }

    setIsSubmitting(true);
    setFormError('');

    try {
      // API call: POST /api/v1/groups/consent/request
      // { parent_email, consent_type: 'social_access' }
      // In production this sends an email to the parent.
      setState((prev) => ({
        ...prev,
        parent_consent_given: true,
        step: 'profile_create',
      }));
    } catch (e: any) {
      setFormError(e?.message ?? 'Could not send consent request.');
    } finally {
      setIsSubmitting(false);
    }
  }, [parentEmail]);

  // --- Step 3: Profile Creation ---

  const validateProfileForm = useCallback((): string | null => {
    const name = displayName.trim();
    if (name.length < MIN_DISPLAY_NAME_LENGTH) {
      return `Display name must be at least ${MIN_DISPLAY_NAME_LENGTH} characters.`;
    }
    if (name.length > MAX_DISPLAY_NAME_LENGTH) {
      return `Display name must be at most ${MAX_DISPLAY_NAME_LENGTH} characters.`;
    }
    if (bio.length > MAX_BIO_LENGTH) {
      return `Bio must be at most ${MAX_BIO_LENGTH} characters.`;
    }
    // Block obviously inappropriate display names
    const blocked = /[<>{}\\\/\[\]]/;
    if (blocked.test(name)) {
      return 'Display name contains invalid characters.';
    }
    return null;
  }, [displayName, bio]);

  const handleCreateProfile = useCallback(async () => {
    const validationError = validateProfileForm();
    if (validationError) {
      setFormError(validationError);
      return;
    }

    setIsSubmitting(true);
    setFormError('');

    try {
      // API call: POST /api/v1/social/profiles
      // { display_name, bio, date_of_birth }
      setState((prev) => ({
        ...prev,
        profile_created: true,
        step: 'complete',
      }));
    } catch (e: any) {
      setFormError(e?.message ?? 'Could not create your profile.');
    } finally {
      setIsSubmitting(false);
    }
  }, [validateProfileForm]);

  // --- Step 4: Complete ---

  const handleFinish = useCallback(() => {
    if (onComplete) {
      onComplete();
    }
  }, [onComplete]);

  // --- Render helpers ---

  const renderStepIndicator = () => {
    const steps: OnboardingStep[] = state.age_estimate !== null && state.age_estimate < CONSENT_AGE_THRESHOLD
      ? ['age_verify', 'parent_consent', 'profile_create', 'complete']
      : ['age_verify', 'profile_create', 'complete'];

    const currentIndex = steps.indexOf(state.step);

    return React.createElement(
      View,
      { style: styles.stepIndicator, accessibilityLabel: `Step ${currentIndex + 1} of ${steps.length}` },
      ...steps.map((s, i) =>
        React.createElement(View, {
          key: s,
          style: [
            styles.stepDot,
            i <= currentIndex ? styles.stepDotActive : styles.stepDotInactive,
          ],
        }),
      ),
    );
  };

  const renderAgeVerifyStep = () =>
    React.createElement(
      View,
      { style: styles.stepContent },
      React.createElement(
        Text,
        { style: styles.stepTitle, accessibilityRole: 'header' },
        'How old are you?',
      ),
      React.createElement(
        Text,
        { style: styles.stepDescription },
        'We need to verify your age so we can give you the best experience.',
      ),
      React.createElement(Button, {
        title: 'Verify My Age',
        onPress: handleStartVerification,
        isLoading: isSubmitting,
        disabled: isSubmitting,
        style: styles.actionButton,
        accessibilityLabel: 'Start age verification',
      }),
    );

  const renderParentConsentStep = () =>
    React.createElement(
      View,
      { style: styles.stepContent },
      React.createElement(
        Text,
        { style: styles.stepTitle, accessibilityRole: 'header' },
        'Parent Permission',
      ),
      React.createElement(
        Text,
        { style: styles.stepDescription },
        'Because you are under 13, we need your parent or guardian to say it\'s okay.',
      ),
      React.createElement(Input, {
        label: "Parent's Email",
        placeholder: 'parent@example.com',
        value: parentEmail,
        onChangeText: setParentEmail,
        autoCapitalize: 'none',
        keyboardType: 'email-address',
        accessibilityLabel: 'Parent email address',
      }),
      React.createElement(Button, {
        title: 'Send Permission Request',
        onPress: handleRequestConsent,
        isLoading: isSubmitting,
        disabled: isSubmitting,
        style: styles.actionButton,
        accessibilityLabel: 'Send permission request to parent',
      }),
    );

  const renderProfileCreateStep = () =>
    React.createElement(
      View,
      { style: styles.stepContent },
      React.createElement(
        Text,
        { style: styles.stepTitle, accessibilityRole: 'header' },
        'Create Your Profile',
      ),
      React.createElement(
        Text,
        { style: styles.stepDescription },
        'Choose a display name that your friends will see.',
      ),
      React.createElement(Input, {
        label: 'Display Name',
        placeholder: 'Your cool name',
        value: displayName,
        onChangeText: setDisplayName,
        maxLength: MAX_DISPLAY_NAME_LENGTH,
        accessibilityLabel: 'Display name',
      }),
      React.createElement(Input, {
        label: 'Bio (optional)',
        placeholder: 'Tell us about yourself',
        value: bio,
        onChangeText: setBio,
        maxLength: MAX_BIO_LENGTH,
        accessibilityLabel: 'Bio',
      }),
      React.createElement(Button, {
        title: 'Create Profile',
        onPress: handleCreateProfile,
        isLoading: isSubmitting,
        disabled: isSubmitting,
        style: styles.actionButton,
        accessibilityLabel: 'Create profile',
      }),
    );

  const renderCompleteStep = () => {
    const tier = state.age_estimate !== null ? getTierForAge(state.age_estimate) : null;
    const tierLabel = tier ? TIER_LABELS[tier] ?? tier : 'Unknown';

    return React.createElement(
      View,
      { style: styles.stepContent },
      React.createElement(
        Text,
        { style: styles.stepTitle, accessibilityRole: 'header' },
        'You\'re all set!',
      ),
      React.createElement(
        Text,
        { style: styles.tierBadge, accessibilityLabel: `Your tier is ${tierLabel}` },
        tierLabel,
      ),
      React.createElement(
        Text,
        { style: styles.stepDescription },
        'Your profile is ready. Let\'s explore!',
      ),
      React.createElement(Button, {
        title: 'Start Exploring',
        onPress: handleFinish,
        style: styles.actionButton,
        accessibilityLabel: 'Finish onboarding and start exploring',
      }),
    );
  };

  // --- Main render ---

  const renderCurrentStep = () => {
    switch (state.step) {
      case 'age_verify':
        return renderAgeVerifyStep();
      case 'parent_consent':
        return renderParentConsentStep();
      case 'profile_create':
        return renderProfileCreateStep();
      case 'complete':
        return renderCompleteStep();
      default:
        return null;
    }
  };

  return React.createElement(
    KeyboardAvoidingView,
    {
      style: styles.container,
      behavior: Platform.OS === 'ios' ? 'padding' : 'height',
      accessibilityLabel: 'Onboarding',
    },
    React.createElement(
      ScrollView,
      {
        contentContainerStyle: styles.scrollContent,
        keyboardShouldPersistTaps: 'handled',
      },

      // Logo
      React.createElement(
        View,
        { style: styles.logoContainer },
        React.createElement(BhapiLogo, { size: 'md' }),
      ),

      // Step indicator
      renderStepIndicator(),

      // Current step content
      renderCurrentStep(),

      // Error message
      formError
        ? React.createElement(
            Text,
            { style: styles.errorText, accessibilityRole: 'alert' },
            formError,
          )
        : null,
    ),
  );
}

// Exported for testing
export { getTierForAge, TIER_LABELS, MIN_DISPLAY_NAME_LENGTH, MAX_DISPLAY_NAME_LENGTH, MAX_BIO_LENGTH, CONSENT_AGE_THRESHOLD };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.xl,
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  stepIndicator: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: spacing.xl,
    gap: 8,
  },
  stepDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  stepDotActive: {
    backgroundColor: colors.brand?.primary ?? '#FF6B35',
  },
  stepDotInactive: {
    backgroundColor: colors.neutral[200],
  },
  stepContent: {
    marginBottom: spacing.lg,
  },
  stepTitle: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    textAlign: 'center',
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  stepDescription: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    textAlign: 'center',
    marginBottom: spacing.xl,
    lineHeight: 22,
    fontFamily: typography.fontFamily,
  },
  actionButton: {
    marginTop: spacing.md,
  },
  tierBadge: {
    fontSize: typography.sizes.xl,
    fontWeight: '600',
    color: colors.brand?.primary ?? '#FF6B35',
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  errorText: {
    color: colors.semantic?.error ?? '#DC2626',
    fontSize: typography.sizes.sm,
    textAlign: 'center',
    marginTop: spacing.md,
    fontFamily: typography.fontFamily,
  },
});
