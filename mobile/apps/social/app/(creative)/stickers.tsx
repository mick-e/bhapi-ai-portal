/**
 * Stickers Screen (P3-F1c)
 *
 * Child-facing sticker browser and personal sticker library.
 * Curated packs are shown by category; children can also create
 * custom stickers via the drawing canvas (256×256).
 *
 * API: GET /api/v1/creative/sticker-packs
 * API: GET /api/v1/creative/stickers?member_id=<id>  (personal library)
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { StickerGrid } from '@bhapi/ui';
import type { Sticker, StickerCategory } from '@bhapi/ui';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export type LibraryTab = 'curated' | 'personal';

export const LIBRARY_TABS: Array<{ label: string; value: LibraryTab }> = [
  { label: 'Sticker Packs', value: 'curated' },
  { label: 'My Stickers', value: 'personal' },
];

// Placeholder curated stickers for development
export const PLACEHOLDER_CURATED_STICKERS: Sticker[] = [
  { id: 'bhapi-1', image_url: 'https://placeholder.bhapi.ai/stickers/smile.png', name: 'Bhapi Smile', category: 'branded' },
  { id: 'bhapi-2', image_url: 'https://placeholder.bhapi.ai/stickers/star.png', name: 'Gold Star', category: 'branded' },
  { id: 'bhapi-3', image_url: 'https://placeholder.bhapi.ai/stickers/heart.png', name: 'Heart', category: 'branded' },
  { id: 'bhapi-4', image_url: 'https://placeholder.bhapi.ai/stickers/thumbs-up.png', name: 'Great Job', category: 'branded' },
  { id: 'sea-1', image_url: 'https://placeholder.bhapi.ai/stickers/sun.png', name: 'Sunshine', category: 'seasonal' },
  { id: 'sea-2', image_url: 'https://placeholder.bhapi.ai/stickers/snowflake.png', name: 'Snowflake', category: 'seasonal' },
  { id: 'sea-3', image_url: 'https://placeholder.bhapi.ai/stickers/leaf.png', name: 'Autumn Leaf', category: 'seasonal' },
  { id: 'sea-4', image_url: 'https://placeholder.bhapi.ai/stickers/flower.png', name: 'Spring Flower', category: 'seasonal' },
  { id: 'edu-1', image_url: 'https://placeholder.bhapi.ai/stickers/book.png', name: 'Reading', category: 'educational' },
  { id: 'edu-2', image_url: 'https://placeholder.bhapi.ai/stickers/math.png', name: 'Math Whiz', category: 'educational' },
  { id: 'edu-3', image_url: 'https://placeholder.bhapi.ai/stickers/science.png', name: 'Science Star', category: 'educational' },
  { id: 'edu-4', image_url: 'https://placeholder.bhapi.ai/stickers/art.png', name: 'Art Expert', category: 'educational' },
];

// ---------------------------------------------------------------------------
// Sub-components (exported for testing)
// ---------------------------------------------------------------------------

export interface LibraryTabBarProps {
  activeTab: LibraryTab;
  onTabChange: (tab: LibraryTab) => void;
}

export function LibraryTabBar({ activeTab, onTabChange }: LibraryTabBarProps) {
  return React.createElement(
    View,
    { style: tabBarStyles.container, accessibilityRole: 'tablist', testID: 'library-tab-bar' },
    ...LIBRARY_TABS.map((tab) =>
      React.createElement(
        TouchableOpacity,
        {
          key: tab.value,
          style: [
            tabBarStyles.tab,
            activeTab === tab.value ? tabBarStyles.tabActive : null,
          ],
          onPress: () => onTabChange(tab.value),
          accessibilityLabel: tab.label,
          accessibilityRole: 'tab',
          accessibilityState: { selected: activeTab === tab.value },
          testID: `library-tab-${tab.value}`,
        },
        React.createElement(
          Text,
          {
            style: [
              tabBarStyles.tabText,
              activeTab === tab.value ? tabBarStyles.tabTextActive : null,
            ],
          },
          tab.label
        )
      )
    )
  );
}

const tabBarStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
    minHeight: 44,
  },
  tabActive: {
    borderBottomColor: colors.primary[600],
  },
  tabText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  tabTextActive: {
    color: colors.primary[700],
    fontWeight: '700',
  },
});

// ---------------------------------------------------------------------------
// Main Screen
// ---------------------------------------------------------------------------

export default function StickersScreen() {
  const [libraryTab, setLibraryTab] = useState<LibraryTab>('curated');
  const [stickerCategory, setStickerCategory] = useState<StickerCategory>('branded');

  // In production, these would come from API hooks
  const curatedStickers = PLACEHOLDER_CURATED_STICKERS;
  const personalStickers: Sticker[] = [];

  const displayStickers = libraryTab === 'curated' ? curatedStickers : personalStickers;

  function handleStickerSelect(sticker: Sticker) {
    // Insert sticker into post composition, story, etc.
    // Placeholder — will be wired in Phase 2 integration
  }

  function handleCreateSticker() {
    // Navigate to drawing screen with 256×256 canvas mode
    // router.push('/(creative)/drawing?mode=sticker&size=256');
    // Placeholder — navigation will be configured in Phase 2
  }

  return React.createElement(
    View,
    { style: styles.container },
    // Header
    React.createElement(
      View,
      { style: styles.header },
      React.createElement(
        Text,
        { style: styles.title },
        '\uD83C\uDFAF Stickers'
      ),
      // Create Sticker button
      React.createElement(
        TouchableOpacity,
        {
          style: styles.createButton,
          onPress: handleCreateSticker,
          accessibilityLabel: 'Create a sticker',
          accessibilityRole: 'button',
          testID: 'create-sticker-button',
        },
        React.createElement(
          Text,
          { style: styles.createButtonText },
          '+ Create'
        )
      )
    ),
    // Library tab bar
    React.createElement(LibraryTabBar, {
      activeTab: libraryTab,
      onTabChange: setLibraryTab,
    }),
    // Personal library empty state
    libraryTab === 'personal' && personalStickers.length === 0
      ? React.createElement(
          View,
          { style: styles.emptyPersonal, testID: 'personal-empty-state' },
          React.createElement(
            Text,
            { style: styles.emptyPersonalEmoji },
            '\uD83C\uDFA8'
          ),
          React.createElement(
            Text,
            { style: styles.emptyPersonalTitle },
            'No stickers yet!'
          ),
          React.createElement(
            Text,
            { style: styles.emptyPersonalSubtitle },
            'Create your own stickers in the drawing canvas.'
          ),
          React.createElement(
            TouchableOpacity,
            {
              style: styles.emptyCreateButton,
              onPress: handleCreateSticker,
              accessibilityLabel: 'Create your first sticker',
              accessibilityRole: 'button',
              testID: 'empty-create-sticker-button',
            },
            React.createElement(
              Text,
              { style: styles.emptyCreateButtonText },
              'Create My First Sticker'
            )
          )
        )
      : React.createElement(StickerGrid, {
          stickers: displayStickers,
          onSelect: handleStickerSelect,
          columns: 4,
          activeCategory: stickerCategory,
          onCategoryChange: setStickerCategory,
          style: styles.grid,
        })
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  title: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  createButton: {
    backgroundColor: colors.primary[600],
    borderRadius: 20,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    minHeight: 36,
    justifyContent: 'center',
  },
  createButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.sm,
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
  grid: {
    flex: 1,
  },
  emptyPersonal: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
  },
  emptyPersonalEmoji: {
    fontSize: 64,
    marginBottom: spacing.md,
  },
  emptyPersonalTitle: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.neutral[700],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  emptyPersonalSubtitle: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    textAlign: 'center',
    marginBottom: spacing.xl,
    fontFamily: typography.fontFamily,
  },
  emptyCreateButton: {
    backgroundColor: colors.primary[600],
    borderRadius: 12,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    minHeight: 48,
    justifyContent: 'center',
  },
  emptyCreateButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
});
