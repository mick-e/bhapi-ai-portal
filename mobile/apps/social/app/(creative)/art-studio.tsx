/**
 * Art Studio Screen (P3-F1c)
 *
 * Child-facing AI art generation screen. Children enter a prompt,
 * generate AI art, view a gallery of past creations, and post
 * approved creations to the social feed.
 *
 * API: POST /api/v1/creative/art
 * API: GET  /api/v1/creative/art?member_id=<id>
 * API: POST /api/v1/social/posts  (post to feed)
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
  FlatList,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Badge } from '@bhapi/ui';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ModerationBadgeStatus = 'pending' | 'approved' | 'rejected';

export interface ArtCreation {
  id: string;
  prompt: string;
  image_url: string | null;
  moderation_status: ModerationBadgeStatus;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Sub-components (exported for testing)
// ---------------------------------------------------------------------------

export interface ModerationBadgeProps {
  status: ModerationBadgeStatus;
}

export function ModerationBadge({ status }: ModerationBadgeProps) {
  const config: Record<ModerationBadgeStatus, { label: string; color: string; bg: string }> = {
    pending: { label: 'Reviewing', color: '#92400E', bg: '#FEF3C7' },
    approved: { label: 'Approved', color: '#065F46', bg: '#D1FAE5' },
    rejected: { label: 'Not Approved', color: '#991B1B', bg: '#FEE2E2' },
  };
  const c = config[status] ?? config.pending;

  return React.createElement(
    View,
    {
      style: [moderationBadgeStyles.container, { backgroundColor: c.bg }],
      accessibilityLabel: `Moderation status: ${c.label}`,
    },
    React.createElement(
      Text,
      { style: [moderationBadgeStyles.text, { color: c.color }] },
      c.label
    )
  );
}

const moderationBadgeStyles = StyleSheet.create({
  container: {
    borderRadius: 12,
    paddingHorizontal: 8,
    paddingVertical: 3,
    alignSelf: 'flex-start',
  },
  text: {
    fontSize: 11,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
});

export interface ArtCardProps {
  creation: ArtCreation;
  onPostToFeed: (id: string) => void;
}

export function ArtCard({ creation, onPostToFeed }: ArtCardProps) {
  return React.createElement(
    View,
    { style: artCardStyles.container, testID: `art-card-${creation.id}` },
    // Placeholder image area
    React.createElement(
      View,
      { style: artCardStyles.imagePlaceholder },
      React.createElement(
        Text,
        { style: artCardStyles.imagePlaceholderText },
        creation.image_url ? '\uD83C\uDFA8' : '\u23F3'
      )
    ),
    // Prompt
    React.createElement(
      Text,
      { style: artCardStyles.prompt, numberOfLines: 2 },
      creation.prompt
    ),
    // Moderation status badge
    React.createElement(ModerationBadge, { status: creation.moderation_status }),
    // Post to Feed button (approved only)
    creation.moderation_status === 'approved'
      ? React.createElement(
          TouchableOpacity,
          {
            style: artCardStyles.postButton,
            onPress: () => onPostToFeed(creation.id),
            accessibilityLabel: 'Post to Feed',
            accessibilityRole: 'button',
            testID: `post-btn-${creation.id}`,
          },
          React.createElement(
            Text,
            { style: artCardStyles.postButtonText },
            'Post to Feed'
          )
        )
      : null
  );
}

const artCardStyles = StyleSheet.create({
  container: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: spacing.sm,
    margin: spacing.xs,
    flex: 1,
    borderWidth: 1,
    borderColor: colors.neutral[200],
  },
  imagePlaceholder: {
    height: 100,
    backgroundColor: colors.neutral[100],
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.xs,
  },
  imagePlaceholderText: {
    fontSize: 32,
  },
  prompt: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[600],
    marginBottom: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  postButton: {
    marginTop: spacing.xs,
    backgroundColor: colors.primary[600],
    borderRadius: 6,
    paddingVertical: 6,
    alignItems: 'center',
    minHeight: 32,
    justifyContent: 'center',
  },
  postButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.xs,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
});

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const MAX_ART_PROMPT_LENGTH = 500;

// ---------------------------------------------------------------------------
// Main Screen
// ---------------------------------------------------------------------------

type GenerateState = 'idle' | 'generating' | 'success' | 'error';

export default function ArtStudioScreen() {
  const [prompt, setPrompt] = useState('');
  const [generateState, setGenerateState] = useState<GenerateState>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [creations, setCreations] = useState<ArtCreation[]>([]);

  const charCount = prompt.trim().length;
  const canGenerate = charCount >= 3 && charCount <= MAX_ART_PROMPT_LENGTH && generateState !== 'generating';

  async function handleGenerate() {
    if (!canGenerate) return;
    setGenerateState('generating');
    setErrorMessage('');

    try {
      // API: POST /api/v1/creative/art
      // const result = await apiClient.post<ArtCreation>('/api/v1/creative/art', { prompt });
      // setCreations((prev) => [result, ...prev]);

      // Placeholder until API is connected
      const placeholder: ArtCreation = {
        id: `temp-${Date.now()}`,
        prompt: prompt.trim(),
        image_url: null,
        moderation_status: 'pending',
        created_at: new Date().toISOString(),
      };
      setCreations((prev) => [placeholder, ...prev]);
      setGenerateState('success');
      setPrompt('');
    } catch (e: any) {
      setErrorMessage(e?.message ?? 'Could not generate art. Please try again.');
      setGenerateState('error');
    }
  }

  function handlePostToFeed(creationId: string) {
    // API: POST /api/v1/social/posts with media reference
    // Placeholder — will be wired in Phase 2
  }

  return React.createElement(
    ScrollView,
    {
      style: styles.container,
      contentContainerStyle: styles.content,
      keyboardShouldPersistTaps: 'handled',
    },
    // Header
    React.createElement(
      Text,
      { style: styles.title },
      '\uD83C\uDFA8 Art Studio'
    ),
    React.createElement(
      Text,
      { style: styles.subtitle },
      'Describe what you want to create!'
    ),
    // Prompt input
    React.createElement(TextInput, {
      style: styles.promptInput,
      placeholder: 'A friendly dragon flying over a rainbow city...',
      placeholderTextColor: colors.neutral[400],
      multiline: true,
      maxLength: MAX_ART_PROMPT_LENGTH + 20,
      value: prompt,
      onChangeText: setPrompt,
      accessibilityLabel: 'Art prompt',
      testID: 'art-prompt-input',
    }),
    // Character counter
    React.createElement(
      View,
      { style: styles.counterRow },
      React.createElement(
        Text,
        {
          style: [
            styles.counter,
            charCount > MAX_ART_PROMPT_LENGTH ? styles.counterOver : null,
          ],
        },
        `${charCount}/${MAX_ART_PROMPT_LENGTH}`
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
    // Generate button
    React.createElement(
      TouchableOpacity,
      {
        style: [styles.generateButton, !canGenerate ? styles.generateButtonDisabled : null],
        onPress: handleGenerate,
        disabled: !canGenerate,
        accessibilityLabel: 'Generate art',
        accessibilityRole: 'button',
        testID: 'generate-button',
      },
      generateState === 'generating'
        ? React.createElement(ActivityIndicator, { size: 'small', color: '#FFFFFF' })
        : React.createElement(
            Text,
            { style: styles.generateButtonText },
            '\u2728 Generate'
          )
    ),
    // Gallery section
    creations.length > 0
      ? React.createElement(
          View,
          { style: styles.gallerySection },
          React.createElement(
            Text,
            { style: styles.galleryTitle },
            'My Creations'
          ),
          React.createElement(
            View,
            { style: styles.galleryGrid },
            ...creations.map((creation) =>
              React.createElement(ArtCard, {
                key: creation.id,
                creation,
                onPostToFeed: handlePostToFeed,
              })
            )
          )
        )
      : React.createElement(
          View,
          { style: styles.emptyGallery },
          React.createElement(
            Text,
            { style: styles.emptyGalleryText },
            'Your creations will appear here!'
          )
        )
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  content: {
    padding: spacing.md,
  },
  title: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    marginBottom: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  subtitle: {
    fontSize: typography.sizes.base,
    color: colors.neutral[600],
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  promptInput: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    padding: spacing.md,
    minHeight: 100,
    fontSize: typography.sizes.base,
    color: colors.neutral[900],
    textAlignVertical: 'top',
    fontFamily: typography.fontFamily,
  },
  counterRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: spacing.xs,
    marginBottom: spacing.sm,
  },
  counter: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  counterOver: {
    color: colors.semantic.error,
    fontWeight: '600',
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  generateButton: {
    backgroundColor: colors.primary[600],
    borderRadius: 12,
    paddingVertical: spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
    marginBottom: spacing.lg,
  },
  generateButtonDisabled: {
    opacity: 0.5,
  },
  generateButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.lg,
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
  gallerySection: {
    marginTop: spacing.sm,
  },
  galleryTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '700',
    color: colors.neutral[900],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  galleryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -spacing.xs,
  },
  emptyGallery: {
    alignItems: 'center',
    padding: spacing.xl,
  },
  emptyGalleryText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
    textAlign: 'center',
  },
});
