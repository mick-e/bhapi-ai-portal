/**
 * Create Post Screen
 *
 * Text input with character counter (age-tier max_post_length),
 * media attachment (camera + gallery), hashtag extraction preview,
 * submit -> moderation status message.
 *
 * API: POST /api/v1/social/posts
 */
import React, { useState, useMemo } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import type { AgeTier } from '@bhapi/config';

// ---------------------------------------------------------------------------
// Age-tier post length limits (mirrors backend TIER_PERMISSIONS)
// ---------------------------------------------------------------------------

export const MAX_POST_LENGTH: Record<string, number> = {
  young: 200,
  preteen: 500,
  teen: 1000,
};

export const MIN_POST_LENGTH = 1;

// ---------------------------------------------------------------------------
// Hashtag extraction
// ---------------------------------------------------------------------------

const HASHTAG_RE = /#([a-zA-Z0-9_]+)/g;

export function extractHashtags(content: string): string[] {
  const matches = content.match(HASHTAG_RE);
  if (!matches) return [];
  return [...new Set(matches.map((m) => m.slice(1).toLowerCase()))];
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

type SubmitState = 'idle' | 'submitting' | 'success' | 'error';

// Default tier — in production, sourced from auth context
const DEFAULT_AGE_TIER: AgeTier = 'teen';

export default function CreatePostScreen() {
  const [content, setContent] = useState('');
  const [submitState, setSubmitState] = useState<SubmitState>('idle');
  const [moderationMessage, setModerationMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [ageTier] = useState<AgeTier>(DEFAULT_AGE_TIER);
  const [mediaIds, setMediaIds] = useState<string[]>([]);

  const maxLength = MAX_POST_LENGTH[ageTier] ?? MAX_POST_LENGTH.teen;
  const charCount = content.length;
  const isOverLimit = charCount > maxLength;
  const canSubmit =
    charCount >= MIN_POST_LENGTH && !isOverLimit && submitState !== 'submitting';

  const hashtags = useMemo(() => extractHashtags(content), [content]);

  async function handleSubmit() {
    if (!canSubmit) return;

    setSubmitState('submitting');
    setErrorMessage('');

    try {
      // API: POST /api/v1/social/posts
      // const response = await apiClient.post<CreatePostResponse>(
      //   '/api/v1/social/posts',
      //   { content, media_ids: mediaIds.length > 0 ? mediaIds : undefined }
      // );
      // setModerationMessage(
      //   response.moderation_status === 'approved'
      //     ? 'Your post is live!'
      //     : 'Your post is being reviewed by our safety team.'
      // );

      // Placeholder:
      setModerationMessage('Your post is being reviewed by our safety team.');
      setSubmitState('success');
    } catch (e: any) {
      setErrorMessage(e?.message ?? 'Could not create post. Please try again.');
      setSubmitState('error');
    }
  }

  function handlePickMedia() {
    // Launch image picker or camera
    // For now, no-op until media module is connected
  }

  if (submitState === 'success') {
    return React.createElement(
      View,
      { style: styles.centered },
      React.createElement(
        Text,
        { style: styles.successText, accessibilityRole: 'alert' },
        moderationMessage
      ),
      React.createElement(
        TouchableOpacity,
        {
          style: styles.doneButton,
          accessibilityLabel: 'Back to feed',
          accessibilityRole: 'button',
          // onPress: () => router.back(),
        },
        React.createElement(
          Text,
          { style: styles.doneButtonText },
          'Back to Feed'
        )
      )
    );
  }

  return React.createElement(
    KeyboardAvoidingView,
    {
      style: styles.container,
      behavior: Platform.OS === 'ios' ? 'padding' : undefined,
    },
    React.createElement(
      ScrollView,
      {
        style: styles.scrollView,
        contentContainerStyle: styles.scrollContent,
        keyboardShouldPersistTaps: 'handled',
      },
      // Title
      React.createElement(
        Text,
        { style: styles.title },
        'Create Post'
      ),

      // Text input
      React.createElement(TextInput, {
        style: [
          styles.textInput,
          isOverLimit ? styles.textInputError : null,
        ],
        placeholder: "What's on your mind?",
        placeholderTextColor: colors.neutral[400],
        multiline: true,
        maxLength: maxLength + 50, // Allow typing over to show warning
        value: content,
        onChangeText: setContent,
        accessibilityLabel: 'Post content',
        testID: 'post-content-input',
      }),

      // Character counter
      React.createElement(
        View,
        { style: styles.counterRow },
        React.createElement(
          Text,
          {
            style: [
              styles.counterText,
              isOverLimit ? styles.counterTextError : null,
            ],
            accessibilityLabel: `${charCount} of ${maxLength} characters`,
          },
          `${charCount}/${maxLength}`
        )
      ),

      // Hashtag preview
      hashtags.length > 0
        ? React.createElement(
            View,
            { style: styles.hashtagPreview, accessibilityLabel: 'Hashtags detected' },
            React.createElement(
              Text,
              { style: styles.hashtagLabel },
              'Hashtags:'
            ),
            React.createElement(
              View,
              { style: styles.hashtagRow },
              ...hashtags.map((tag) =>
                React.createElement(
                  View,
                  { key: tag, style: styles.hashtagChip },
                  React.createElement(
                    Text,
                    { style: styles.hashtagChipText },
                    `#${tag}`
                  )
                )
              )
            )
          )
        : null,

      // Media attach button
      React.createElement(
        TouchableOpacity,
        {
          style: styles.mediaButton,
          onPress: handlePickMedia,
          accessibilityLabel: 'Attach media',
          accessibilityRole: 'button',
        },
        React.createElement(
          Text,
          { style: styles.mediaButtonText },
          mediaIds.length > 0
            ? `${mediaIds.length} media attached`
            : 'Add Photo or Video'
        )
      ),

      // Error message
      errorMessage
        ? React.createElement(
            Text,
            { style: styles.errorText, accessibilityRole: 'alert' },
            errorMessage
          )
        : null,

      // Submit button
      React.createElement(
        TouchableOpacity,
        {
          style: [
            styles.submitButton,
            !canSubmit ? styles.submitButtonDisabled : null,
          ],
          onPress: handleSubmit,
          disabled: !canSubmit,
          accessibilityLabel: 'Post',
          accessibilityRole: 'button',
        },
        submitState === 'submitting'
          ? React.createElement(ActivityIndicator, {
              size: 'small',
              color: '#FFFFFF',
            })
          : React.createElement(
              Text,
              { style: styles.submitButtonText },
              'Post'
            )
      )
    )
  );
}

// Exported for testing
export { type SubmitState };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: spacing.md,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.neutral[50],
    padding: spacing.md,
  },
  title: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.neutral[900],
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  textInput: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    padding: spacing.md,
    minHeight: 120,
    fontSize: typography.sizes.base,
    color: colors.neutral[900],
    textAlignVertical: 'top',
    fontFamily: typography.fontFamily,
  },
  textInputError: {
    borderColor: colors.semantic.error,
  },
  counterRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: spacing.xs,
    marginBottom: spacing.md,
  },
  counterText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  counterTextError: {
    color: colors.semantic.error,
    fontWeight: '600',
  },
  hashtagPreview: {
    marginBottom: spacing.md,
  },
  hashtagLabel: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[600],
    marginBottom: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  hashtagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
  },
  hashtagChip: {
    backgroundColor: colors.primary[100],
    borderRadius: 12,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
  },
  hashtagChipText: {
    fontSize: typography.sizes.sm,
    color: colors.primary[700],
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  mediaButton: {
    borderWidth: 1,
    borderColor: colors.neutral[300],
    borderStyle: 'dashed',
    borderRadius: 8,
    padding: spacing.md,
    alignItems: 'center',
    marginBottom: spacing.md,
    minHeight: 44,
    justifyContent: 'center',
  },
  mediaButtonText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[600],
    fontFamily: typography.fontFamily,
  },
  submitButton: {
    backgroundColor: colors.primary[600],
    borderRadius: 8,
    padding: spacing.md,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  submitButtonDisabled: {
    opacity: 0.5,
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  successText: {
    fontSize: typography.sizes.lg,
    color: colors.semantic.success,
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  doneButton: {
    backgroundColor: colors.primary[600],
    borderRadius: 8,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    minHeight: 44,
    justifyContent: 'center',
  },
  doneButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
});
