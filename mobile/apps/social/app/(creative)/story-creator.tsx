/**
 * Story Creator Screen (P3-F1c)
 *
 * Child-facing story creation screen. Children browse templates by theme,
 * select one, write their story, and post it to the social feed.
 *
 * Templates:
 *   - young (5-9): fill_in_blank style
 *   - preteen (10-12): guided_outline style
 *   - teen (13-15): free_write style
 *
 * API: GET  /api/v1/creative/story-templates?age_tier=<tier>
 * API: POST /api/v1/creative/stories
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
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import type { AgeTier } from '@bhapi/config';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type StoryTheme =
  | 'adventure'
  | 'friendship'
  | 'mystery'
  | 'science'
  | 'fantasy'
  | 'humor';

export type StoryTemplateType = 'fill_in_blank' | 'guided_outline' | 'free_write';

export interface StoryTemplate {
  id: string;
  theme: StoryTheme;
  title: string;
  preview: string;
  template_type: StoryTemplateType;
  age_tiers: AgeTier[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const STORY_THEMES: Array<{ label: string; value: StoryTheme; emoji: string }> = [
  { label: 'Adventure', value: 'adventure', emoji: '\uD83C\uDFD4\uFE0F' },
  { label: 'Friendship', value: 'friendship', emoji: '\uD83D\uDC95' },
  { label: 'Mystery', value: 'mystery', emoji: '\uD83D\uDD0D' },
  { label: 'Science', value: 'science', emoji: '\uD83D\uDD2C' },
  { label: 'Fantasy', value: 'fantasy', emoji: '\uD83E\uDD84' },
  { label: 'Humor', value: 'humor', emoji: '\uD83D\uDE02' },
];

export const DEFAULT_AGE_TIER: AgeTier = 'teen';

export const MAX_STORY_LENGTH = 2000;

// Template type by age tier
export function getTemplateTypeForTier(ageTier: AgeTier): StoryTemplateType {
  if (ageTier === 'young') return 'fill_in_blank';
  if (ageTier === 'preteen') return 'guided_outline';
  return 'free_write';
}

// ---------------------------------------------------------------------------
// Sub-components (exported for testing)
// ---------------------------------------------------------------------------

export interface ThemeTabsProps {
  activeTheme: StoryTheme;
  onThemeChange: (theme: StoryTheme) => void;
}

export function ThemeTabs({ activeTheme, onThemeChange }: ThemeTabsProps) {
  return React.createElement(
    ScrollView,
    {
      horizontal: true,
      showsHorizontalScrollIndicator: false,
      style: themeTabsStyles.container,
      contentContainerStyle: themeTabsStyles.content,
      accessibilityRole: 'tablist',
      testID: 'theme-tabs',
    },
    ...STORY_THEMES.map((theme) =>
      React.createElement(
        TouchableOpacity,
        {
          key: theme.value,
          style: [
            themeTabsStyles.tab,
            activeTheme === theme.value ? themeTabsStyles.tabActive : null,
          ],
          onPress: () => onThemeChange(theme.value),
          accessibilityLabel: `${theme.label} theme`,
          accessibilityRole: 'tab',
          accessibilityState: { selected: activeTheme === theme.value },
          testID: `theme-tab-${theme.value}`,
        },
        React.createElement(
          Text,
          { style: themeTabsStyles.emoji },
          theme.emoji
        ),
        React.createElement(
          Text,
          {
            style: [
              themeTabsStyles.label,
              activeTheme === theme.value ? themeTabsStyles.labelActive : null,
            ],
          },
          theme.label
        )
      )
    )
  );
}

const themeTabsStyles = StyleSheet.create({
  container: {
    maxHeight: 56,
  },
  content: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  tab: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    marginRight: spacing.sm,
    borderRadius: 20,
    backgroundColor: colors.neutral[100],
    borderWidth: 1,
    borderColor: 'transparent',
    minHeight: 36,
  },
  tabActive: {
    backgroundColor: colors.primary[100],
    borderColor: colors.primary[400],
  },
  emoji: {
    fontSize: 16,
    marginRight: 4,
  },
  label: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[600],
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  labelActive: {
    color: colors.primary[700],
    fontWeight: '600',
  },
});

export interface TemplateCardProps {
  template: StoryTemplate;
  isSelected: boolean;
  onSelect: (template: StoryTemplate) => void;
}

export function TemplateCard({ template, isSelected, onSelect }: TemplateCardProps) {
  return React.createElement(
    TouchableOpacity,
    {
      style: [templateCardStyles.container, isSelected ? templateCardStyles.containerSelected : null],
      onPress: () => onSelect(template),
      accessibilityLabel: template.title,
      accessibilityRole: 'button',
      accessibilityState: { selected: isSelected },
      testID: `template-card-${template.id}`,
    },
    React.createElement(
      Text,
      { style: templateCardStyles.title },
      template.title
    ),
    React.createElement(
      Text,
      { style: templateCardStyles.preview, numberOfLines: 2 },
      template.preview
    ),
    React.createElement(
      View,
      { style: templateCardStyles.typeBadge },
      React.createElement(
        Text,
        { style: templateCardStyles.typeText },
        template.template_type.replace('_', ' ')
      )
    )
  );
}

const templateCardStyles = StyleSheet.create({
  container: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.sm,
    borderWidth: 2,
    borderColor: colors.neutral[200],
  },
  containerSelected: {
    borderColor: colors.primary[500],
    backgroundColor: colors.primary[50],
  },
  title: {
    fontSize: typography.sizes.base,
    fontWeight: '700',
    color: colors.neutral[900],
    marginBottom: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  preview: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[600],
    fontFamily: typography.fontFamily,
    marginBottom: spacing.xs,
  },
  typeBadge: {
    alignSelf: 'flex-start',
    backgroundColor: colors.neutral[100],
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  typeText: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
    textTransform: 'capitalize',
  },
});

// ---------------------------------------------------------------------------
// Placeholder templates for development/demo
// ---------------------------------------------------------------------------

export const PLACEHOLDER_TEMPLATES: StoryTemplate[] = [
  {
    id: 'adv-1',
    theme: 'adventure',
    title: 'The Hidden Map',
    preview: 'You found an old map in your attic. Where does it lead?',
    template_type: 'free_write',
    age_tiers: ['teen', 'preteen'],
  },
  {
    id: 'adv-2',
    theme: 'adventure',
    title: 'My Magical Journey',
    preview: 'One day, I found a magic ___. It took me to ___.',
    template_type: 'fill_in_blank',
    age_tiers: ['young'],
  },
  {
    id: 'fri-1',
    theme: 'friendship',
    title: 'The New Kid',
    preview: 'A new student arrives at school and needs a friend.',
    template_type: 'guided_outline',
    age_tiers: ['preteen', 'teen'],
  },
  {
    id: 'mys-1',
    theme: 'mystery',
    title: 'The Missing Trophy',
    preview: 'The school trophy has vanished! Can you solve the mystery?',
    template_type: 'free_write',
    age_tiers: ['teen', 'preteen'],
  },
  {
    id: 'sci-1',
    theme: 'science',
    title: 'My Robot Friend',
    preview: 'I built a robot named ___. Its special power was ___.',
    template_type: 'fill_in_blank',
    age_tiers: ['young'],
  },
  {
    id: 'fan-1',
    theme: 'fantasy',
    title: 'The Dragon\u2019s Request',
    preview: 'A young dragon comes to you for help. What do they need?',
    template_type: 'free_write',
    age_tiers: ['teen', 'preteen'],
  },
  {
    id: 'hum-1',
    theme: 'humor',
    title: 'When My Pet Talked',
    preview: 'One morning, my pet ___ said ___. I couldn\u2019t believe it!',
    template_type: 'fill_in_blank',
    age_tiers: ['young', 'preteen'],
  },
];

// ---------------------------------------------------------------------------
// Main Screen
// ---------------------------------------------------------------------------

type SubmitState = 'idle' | 'submitting' | 'success' | 'error';

export default function StoryCreatorScreen() {
  const [ageTier] = useState<AgeTier>(DEFAULT_AGE_TIER);
  const [activeTheme, setActiveTheme] = useState<StoryTheme>('adventure');
  const [selectedTemplate, setSelectedTemplate] = useState<StoryTemplate | null>(null);
  const [storyContent, setStoryContent] = useState('');
  const [submitState, setSubmitState] = useState<SubmitState>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  const preferredType = getTemplateTypeForTier(ageTier);

  // Filter templates by theme and age tier
  const filteredTemplates = PLACEHOLDER_TEMPLATES.filter(
    (t) => t.theme === activeTheme && t.age_tiers.includes(ageTier)
  );

  // If no templates match, show the age-appropriate type from all themes
  const displayTemplates =
    filteredTemplates.length > 0
      ? filteredTemplates
      : PLACEHOLDER_TEMPLATES.filter((t) => t.theme === activeTheme).slice(0, 2);

  const charCount = storyContent.length;
  const canSubmit =
    selectedTemplate !== null &&
    charCount >= 10 &&
    charCount <= MAX_STORY_LENGTH &&
    submitState !== 'submitting';

  async function handlePostToFeed() {
    if (!canSubmit) return;
    setSubmitState('submitting');
    setErrorMessage('');

    try {
      // API: POST /api/v1/creative/stories
      // const story = await apiClient.post('/api/v1/creative/stories', {
      //   template_id: selectedTemplate!.id,
      //   content: storyContent,
      // });
      // API: POST /api/v1/social/posts
      // await apiClient.post('/api/v1/social/posts', { content: storyContent });

      setSubmitState('success');
    } catch (e: any) {
      setErrorMessage(e?.message ?? 'Could not post story. Please try again.');
      setSubmitState('error');
    }
  }

  if (submitState === 'success') {
    return React.createElement(
      View,
      { style: styles.successContainer },
      React.createElement(Text, { style: styles.successEmoji }, '\uD83C\uDF89'),
      React.createElement(Text, { style: styles.successTitle }, 'Story Posted!'),
      React.createElement(
        Text,
        { style: styles.successSubtitle },
        'Your story is being reviewed by our safety team.'
      ),
      React.createElement(
        TouchableOpacity,
        {
          style: styles.doneButton,
          onPress: () => {
            setSubmitState('idle');
            setStoryContent('');
            setSelectedTemplate(null);
          },
          accessibilityLabel: 'Write another story',
          accessibilityRole: 'button',
        },
        React.createElement(
          Text,
          { style: styles.doneButtonText },
          'Write Another Story'
        )
      )
    );
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
      '\uD83D\uDCDD Story Creator'
    ),
    // Theme tabs
    React.createElement(ThemeTabs, {
      activeTheme,
      onThemeChange: (theme) => {
        setActiveTheme(theme);
        setSelectedTemplate(null);
      },
    }),
    // Template browser
    React.createElement(
      View,
      { style: styles.templatesSection },
      React.createElement(
        Text,
        { style: styles.sectionLabel },
        'Choose a starter:'
      ),
      displayTemplates.length > 0
        ? displayTemplates.map((template) =>
            React.createElement(TemplateCard, {
              key: template.id,
              template,
              isSelected: selectedTemplate?.id === template.id,
              onSelect: (t) => {
                setSelectedTemplate(t);
                if (ageTier === 'young' && t.template_type === 'fill_in_blank') {
                  setStoryContent(t.preview);
                } else {
                  setStoryContent('');
                }
              },
            })
          )
        : React.createElement(
            Text,
            { style: styles.noTemplates },
            'No templates for this theme yet!'
          )
    ),
    // Story writing area
    selectedTemplate
      ? React.createElement(
          View,
          { style: styles.writingSection },
          React.createElement(
            Text,
            { style: styles.sectionLabel },
            'Write your story:'
          ),
          React.createElement(TextInput, {
            style: styles.storyInput,
            placeholder:
              preferredType === 'fill_in_blank'
                ? 'Fill in the blanks above...'
                : 'Write your story here...',
            placeholderTextColor: colors.neutral[400],
            multiline: true,
            maxLength: MAX_STORY_LENGTH + 50,
            value: storyContent,
            onChangeText: setStoryContent,
            accessibilityLabel: 'Story content',
            testID: 'story-input',
          }),
          React.createElement(
            View,
            { style: styles.counterRow },
            React.createElement(
              Text,
              {
                style: [
                  styles.counter,
                  charCount > MAX_STORY_LENGTH ? styles.counterOver : null,
                ],
              },
              `${charCount}/${MAX_STORY_LENGTH}`
            )
          ),
          errorMessage
            ? React.createElement(
                Text,
                { style: styles.errorText, accessibilityRole: 'alert' },
                errorMessage
              )
            : null,
          React.createElement(
            TouchableOpacity,
            {
              style: [styles.postButton, !canSubmit ? styles.postButtonDisabled : null],
              onPress: handlePostToFeed,
              disabled: !canSubmit,
              accessibilityLabel: 'Post to Feed',
              accessibilityRole: 'button',
              testID: 'post-to-feed-button',
            },
            submitState === 'submitting'
              ? React.createElement(ActivityIndicator, { size: 'small', color: '#FFFFFF' })
              : React.createElement(
                  Text,
                  { style: styles.postButtonText },
                  'Post to Feed'
                )
          )
        )
      : null
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
    paddingBottom: spacing.xl,
  },
  title: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    padding: spacing.md,
    paddingBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  templatesSection: {
    padding: spacing.md,
    paddingTop: spacing.sm,
  },
  sectionLabel: {
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    color: colors.neutral[500],
    marginBottom: spacing.sm,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    fontFamily: typography.fontFamily,
  },
  noTemplates: {
    fontSize: typography.sizes.base,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
    textAlign: 'center',
    paddingVertical: spacing.md,
  },
  writingSection: {
    padding: spacing.md,
    paddingTop: 0,
  },
  storyInput: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    padding: spacing.md,
    minHeight: 200,
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
  postButton: {
    backgroundColor: colors.primary[600],
    borderRadius: 12,
    paddingVertical: spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  postButtonDisabled: {
    opacity: 0.5,
  },
  postButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
  successContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
    backgroundColor: colors.neutral[50],
  },
  successEmoji: {
    fontSize: 64,
    marginBottom: spacing.md,
  },
  successTitle: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  successSubtitle: {
    fontSize: typography.sizes.base,
    color: colors.neutral[600],
    textAlign: 'center',
    marginBottom: spacing.xl,
    fontFamily: typography.fontFamily,
  },
  doneButton: {
    backgroundColor: colors.primary[600],
    borderRadius: 12,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    minHeight: 48,
    justifyContent: 'center',
  },
  doneButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
});
