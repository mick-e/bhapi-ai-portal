/**
 * StickerGrid — Grid display of stickers with category tabs.
 *
 * Features:
 *   - Category tabs: branded, seasonal, educational, my stickers
 *   - FlatList grid of sticker images with names below
 *   - Pressable sticker items
 *
 * Used in the social app stickers screen (child-facing).
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  FlatList,
  Image,
  StyleSheet,
  ViewStyle,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type StickerCategory = 'branded' | 'seasonal' | 'educational' | 'my_stickers';

export interface Sticker {
  id: string;
  image_url: string;
  name: string;
  category?: StickerCategory;
}

export interface StickerGridProps {
  /** Array of sticker objects to display. */
  stickers: Sticker[];
  /** Called when a sticker is selected. */
  onSelect: (sticker: Sticker) => void;
  /** Number of columns (default: 4). */
  columns?: number;
  /** Currently active category tab. */
  activeCategory?: StickerCategory;
  /** Called when a category tab is tapped. */
  onCategoryChange?: (category: StickerCategory) => void;
  /** Custom style overrides for the container. */
  style?: ViewStyle;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const STICKER_CATEGORIES: Array<{ label: string; value: StickerCategory }> = [
  { label: 'Bhapi', value: 'branded' },
  { label: 'Seasonal', value: 'seasonal' },
  { label: 'Learn', value: 'educational' },
  { label: 'Mine', value: 'my_stickers' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function StickerGrid({
  stickers,
  onSelect,
  columns = 4,
  activeCategory = 'branded',
  onCategoryChange,
  style,
}: StickerGridProps) {
  const [localCategory, setLocalCategory] = useState<StickerCategory>(activeCategory);

  const currentCategory = onCategoryChange ? activeCategory : localCategory;

  function handleCategoryPress(category: StickerCategory) {
    if (onCategoryChange) {
      onCategoryChange(category);
    } else {
      setLocalCategory(category);
    }
  }

  const filteredStickers = stickers.filter(
    (s) => !s.category || s.category === currentCategory
  );

  function renderSticker({ item }: { item: Sticker }) {
    return React.createElement(
      TouchableOpacity,
      {
        style: styles.stickerItem,
        onPress: () => onSelect(item),
        accessibilityLabel: item.name,
        accessibilityRole: 'button',
        testID: `sticker-${item.id}`,
      },
      React.createElement(Image, {
        source: { uri: item.image_url },
        style: styles.stickerImage,
        resizeMode: 'contain',
        accessibilityLabel: item.name,
      }),
      React.createElement(
        Text,
        {
          style: styles.stickerName,
          numberOfLines: 1,
        },
        item.name
      )
    );
  }

  return React.createElement(
    View,
    { style: [styles.container, style] },
    // Category tabs
    React.createElement(
      View,
      { style: styles.tabs, accessibilityRole: 'tablist' },
      ...STICKER_CATEGORIES.map((cat) =>
        React.createElement(
          TouchableOpacity,
          {
            key: cat.value,
            style: [
              styles.tab,
              currentCategory === cat.value ? styles.tabActive : null,
            ],
            onPress: () => handleCategoryPress(cat.value),
            accessibilityLabel: cat.label,
            accessibilityRole: 'tab',
            accessibilityState: { selected: currentCategory === cat.value },
            testID: `tab-${cat.value}`,
          },
          React.createElement(
            Text,
            {
              style: [
                styles.tabText,
                currentCategory === cat.value ? styles.tabTextActive : null,
              ],
            },
            cat.label
          )
        )
      )
    ),
    // Sticker grid
    filteredStickers.length === 0
      ? React.createElement(
          View,
          { style: styles.emptyState },
          React.createElement(
            Text,
            { style: styles.emptyText },
            'No stickers yet!'
          )
        )
      : React.createElement(FlatList as any, {
          data: filteredStickers,
          renderItem: renderSticker,
          keyExtractor: (item: Sticker) => item.id,
          numColumns: columns,
          key: `grid-${columns}`,
          contentContainerStyle: styles.grid,
          columnWrapperStyle: columns > 1 ? styles.row : undefined,
          showsVerticalScrollIndicator: false,
          testID: 'sticker-grid',
        })
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

export const stickerGridStyles = {
  tabHeight: 40,
  itemSize: 72,
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  tabs: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
    backgroundColor: '#FFFFFF',
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
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
    color: colors.primary[600],
    fontWeight: '600',
  },
  grid: {
    padding: spacing.sm,
  },
  row: {
    justifyContent: 'flex-start',
  },
  stickerItem: {
    alignItems: 'center',
    margin: spacing.xs,
    width: 72,
  },
  stickerImage: {
    width: 56,
    height: 56,
    borderRadius: 8,
    backgroundColor: colors.neutral[100],
  },
  stickerName: {
    marginTop: 4,
    fontSize: typography.sizes.xs,
    color: colors.neutral[600],
    textAlign: 'center',
    fontFamily: typography.fontFamily,
    maxWidth: 72,
  },
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
  },
  emptyText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
    textAlign: 'center',
  },
});
