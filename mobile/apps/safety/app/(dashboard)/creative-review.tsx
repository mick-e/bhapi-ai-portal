/**
 * Creative Review Screen (P3-F1c)
 *
 * Parent-facing screen to review children's creative content
 * (AI art, stories, drawings). Shows moderation status and lets
 * parents flag content for additional review.
 *
 * API: GET  /api/v1/creative/content?member_id=<id>&type=<type>&status=<status>
 * API: POST /api/v1/moderation/flag  (parent flag)
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Badge, Card } from '@bhapi/ui';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ContentType = 'art' | 'story' | 'drawing';
export type ModerationStatus = 'pending' | 'approved' | 'rejected' | 'flagged';
export type FilterTab = 'all' | 'pending' | 'approved' | 'flagged';

export interface CreativeItem {
  id: string;
  member_id: string;
  member_name: string;
  content_type: ContentType;
  title: string;
  preview: string;
  moderation_status: ModerationStatus;
  created_at: string;
  is_flagged_by_parent: boolean;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const FILTER_TABS: Array<{ label: string; value: FilterTab }> = [
  { label: 'All', value: 'all' },
  { label: 'Pending Review', value: 'pending' },
  { label: 'Approved', value: 'approved' },
  { label: 'Flagged', value: 'flagged' },
];

export const CONTENT_TYPE_LABELS: Record<ContentType, string> = {
  art: 'AI Art',
  story: 'Story',
  drawing: 'Drawing',
};

export const CONTENT_TYPE_EMOJI: Record<ContentType, string> = {
  art: '\uD83C\uDFA8',
  story: '\uD83D\uDCDD',
  drawing: '\u270F\uFE0F',
};

// ---------------------------------------------------------------------------
// Sub-components (exported for testing)
// ---------------------------------------------------------------------------

export interface FilterTabBarProps {
  activeFilter: FilterTab;
  onFilterChange: (filter: FilterTab) => void;
}

export function FilterTabBar({ activeFilter, onFilterChange }: FilterTabBarProps) {
  return React.createElement(
    ScrollView,
    {
      horizontal: true,
      showsHorizontalScrollIndicator: false,
      style: filterTabStyles.scroll,
      contentContainerStyle: filterTabStyles.content,
      accessibilityRole: 'tablist',
      testID: 'filter-tab-bar',
    },
    ...FILTER_TABS.map((tab) =>
      React.createElement(
        TouchableOpacity,
        {
          key: tab.value,
          style: [
            filterTabStyles.tab,
            activeFilter === tab.value ? filterTabStyles.tabActive : null,
          ],
          onPress: () => onFilterChange(tab.value),
          accessibilityLabel: `Filter: ${tab.label}`,
          accessibilityRole: 'tab',
          accessibilityState: { selected: activeFilter === tab.value },
          testID: `filter-tab-${tab.value}`,
        },
        React.createElement(
          Text,
          {
            style: [
              filterTabStyles.tabText,
              activeFilter === tab.value ? filterTabStyles.tabTextActive : null,
            ],
          },
          tab.label
        )
      )
    )
  );
}

const filterTabStyles = StyleSheet.create({
  scroll: {
    maxHeight: 48,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  content: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  tab: {
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    marginRight: spacing.sm,
    borderRadius: 16,
    backgroundColor: colors.neutral[100],
    borderWidth: 1,
    borderColor: 'transparent',
    minHeight: 32,
    justifyContent: 'center',
  },
  tabActive: {
    backgroundColor: colors.primary[100],
    borderColor: colors.primary[400],
  },
  tabText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[600],
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  tabTextActive: {
    color: colors.primary[700],
    fontWeight: '700',
  },
});

export interface ModerationStatusBadgeProps {
  status: ModerationStatus;
}

export function ModerationStatusBadge({ status }: ModerationStatusBadgeProps) {
  const config: Record<ModerationStatus, { label: string; color: string; bg: string }> = {
    pending: { label: 'Pending Review', color: '#92400E', bg: '#FEF3C7' },
    approved: { label: 'Approved', color: '#065F46', bg: '#D1FAE5' },
    rejected: { label: 'Not Approved', color: '#991B1B', bg: '#FEE2E2' },
    flagged: { label: 'Flagged', color: '#7C3AED', bg: '#EDE9FE' },
  };
  const c = config[status] ?? config.pending;

  return React.createElement(
    View,
    {
      style: [statusBadgeStyles.container, { backgroundColor: c.bg }],
      accessibilityLabel: `Moderation status: ${c.label}`,
      testID: `status-badge-${status}`,
    },
    React.createElement(
      Text,
      { style: [statusBadgeStyles.text, { color: c.color }] },
      c.label
    )
  );
}

const statusBadgeStyles = StyleSheet.create({
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

export interface CreativeItemCardProps {
  item: CreativeItem;
  onFlag: (id: string) => void;
  isFlagging: boolean;
}

export function CreativeItemCard({ item, onFlag, isFlagging }: CreativeItemCardProps) {
  return React.createElement(
    View,
    {
      style: creativeCardStyles.container,
      testID: `creative-item-${item.id}`,
    },
    // Header row
    React.createElement(
      View,
      { style: creativeCardStyles.header },
      React.createElement(
        Text,
        { style: creativeCardStyles.typeLabel },
        `${CONTENT_TYPE_EMOJI[item.content_type]} ${CONTENT_TYPE_LABELS[item.content_type]}`
      ),
      React.createElement(
        Text,
        { style: creativeCardStyles.memberName },
        item.member_name
      )
    ),
    // Title
    React.createElement(
      Text,
      { style: creativeCardStyles.title, numberOfLines: 1 },
      item.title
    ),
    // Preview
    React.createElement(
      Text,
      { style: creativeCardStyles.preview, numberOfLines: 2 },
      item.preview
    ),
    // Footer: status + flag button
    React.createElement(
      View,
      { style: creativeCardStyles.footer },
      React.createElement(ModerationStatusBadge, { status: item.moderation_status }),
      item.is_flagged_by_parent
        ? React.createElement(
            View,
            { style: creativeCardStyles.flaggedIndicator },
            React.createElement(
              Text,
              { style: creativeCardStyles.flaggedText },
              '\uD83D\uDEA9 Flagged by you'
            )
          )
        : React.createElement(
            TouchableOpacity,
            {
              style: creativeCardStyles.flagButton,
              onPress: () => onFlag(item.id),
              disabled: isFlagging,
              accessibilityLabel: `Flag ${item.title} for review`,
              accessibilityRole: 'button',
              testID: `flag-button-${item.id}`,
            },
            isFlagging
              ? React.createElement(ActivityIndicator, { size: 'small', color: colors.semantic.error })
              : React.createElement(
                  Text,
                  { style: creativeCardStyles.flagButtonText },
                  'Flag for Review'
                )
          )
    ),
    // Date
    React.createElement(
      Text,
      { style: creativeCardStyles.date },
      new Date(item.created_at).toLocaleDateString()
    )
  );
}

const creativeCardStyles = StyleSheet.create({
  container: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.neutral[200],
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  typeLabel: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  memberName: {
    fontSize: typography.sizes.sm,
    color: colors.primary[700],
    fontWeight: '600',
    fontFamily: typography.fontFamily,
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
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  flagButton: {
    backgroundColor: '#FEF2F2',
    borderRadius: 8,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderWidth: 1,
    borderColor: '#FCA5A5',
    minHeight: 32,
    justifyContent: 'center',
  },
  flagButtonText: {
    color: '#991B1B',
    fontSize: typography.sizes.xs,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  flaggedIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  flaggedText: {
    fontSize: typography.sizes.xs,
    color: '#7C3AED',
    fontFamily: typography.fontFamily,
    fontWeight: '600',
  },
  date: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
    textAlign: 'right',
  },
});

// ---------------------------------------------------------------------------
// Placeholder data for development
// ---------------------------------------------------------------------------

export const PLACEHOLDER_CREATIVE_ITEMS: CreativeItem[] = [
  {
    id: 'item-1',
    member_id: 'child-1',
    member_name: 'Alex',
    content_type: 'art',
    title: 'Space Dragon',
    preview: 'A friendly dragon flying through a rainbow galaxy.',
    moderation_status: 'approved',
    created_at: new Date().toISOString(),
    is_flagged_by_parent: false,
  },
  {
    id: 'item-2',
    member_id: 'child-1',
    member_name: 'Alex',
    content_type: 'story',
    title: 'The Hidden Map',
    preview: 'One day I found an old treasure map in my attic...',
    moderation_status: 'pending',
    created_at: new Date().toISOString(),
    is_flagged_by_parent: false,
  },
  {
    id: 'item-3',
    member_id: 'child-2',
    member_name: 'Jordan',
    content_type: 'drawing',
    title: 'My Robot Friend',
    preview: 'A drawing of a robot named Sparky.',
    moderation_status: 'approved',
    created_at: new Date().toISOString(),
    is_flagged_by_parent: false,
  },
];

// ---------------------------------------------------------------------------
// Main Screen
// ---------------------------------------------------------------------------

export default function CreativeReviewScreen() {
  const [activeFilter, setActiveFilter] = useState<FilterTab>('all');
  const [items, setItems] = useState<CreativeItem[]>(PLACEHOLDER_CREATIVE_ITEMS);
  const [flaggingId, setFlaggingId] = useState<string | null>(null);

  // Filter items based on active tab
  const filteredItems = items.filter((item) => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'pending') return item.moderation_status === 'pending';
    if (activeFilter === 'approved') return item.moderation_status === 'approved';
    if (activeFilter === 'flagged') return item.is_flagged_by_parent || item.moderation_status === 'flagged';
    return true;
  });

  async function handleFlag(itemId: string) {
    setFlaggingId(itemId);

    try {
      // API: POST /api/v1/moderation/flag
      // await apiClient.post('/api/v1/moderation/flag', {
      //   content_id: itemId,
      //   flagged_by: 'parent',
      // });

      setItems((prev) =>
        prev.map((item) =>
          item.id === itemId ? { ...item, is_flagged_by_parent: true } : item
        )
      );
    } finally {
      setFlaggingId(null);
    }
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
        'Creative Content'
      ),
      React.createElement(
        Text,
        { style: styles.subtitle },
        'Review your children\u2019s creative work'
      )
    ),
    // Filter tabs
    React.createElement(FilterTabBar, {
      activeFilter,
      onFilterChange: setActiveFilter,
    }),
    // Content list
    React.createElement(
      ScrollView,
      {
        style: styles.scrollView,
        contentContainerStyle: styles.scrollContent,
        showsVerticalScrollIndicator: false,
      },
      filteredItems.length === 0
        ? React.createElement(
            View,
            { style: styles.emptyState, testID: 'empty-state' },
            React.createElement(
              Text,
              { style: styles.emptyEmoji },
              '\uD83C\uDFA8'
            ),
            React.createElement(
              Text,
              { style: styles.emptyText },
              activeFilter === 'all'
                ? 'No creative content yet!'
                : `No ${activeFilter} content.`
            )
          )
        : filteredItems.map((item) =>
            React.createElement(CreativeItemCard, {
              key: item.id,
              item,
              onFlag: handleFlag,
              isFlagging: flaggingId === item.id,
            })
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
  header: {
    backgroundColor: '#FFFFFF',
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  title: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  subtitle: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
    marginTop: 2,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: spacing.md,
    paddingBottom: spacing.xl,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xl * 2,
  },
  emptyEmoji: {
    fontSize: 48,
    marginBottom: spacing.md,
  },
  emptyText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
    textAlign: 'center',
  },
});
