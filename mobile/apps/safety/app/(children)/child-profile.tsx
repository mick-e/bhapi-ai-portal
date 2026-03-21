/**
 * Child Profile Screen (P2-M4)
 *
 * Combined AI + social timeline, risk trend chart (7/30d),
 * platform breakdown, and quick actions.
 *
 * API: GET /api/v1/portal/child-profile?member_id=<id>
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Card, Badge, Avatar, Button } from '@bhapi/ui';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TimelineItem {
  id: string;
  source: string; // ai, social_post, social_message, risk, moderation
  event_type: string;
  title: string;
  detail: string;
  severity: string | null;
  platform: string | null;
  timestamp: string;
}

interface RiskTrendPoint {
  date: string;
  count: number;
  high_count: number;
}

interface PlatformBreakdown {
  platform: string;
  event_count: number;
  percentage: number;
}

interface ChildProfileData {
  member_id: string;
  member_name: string;
  avatar_url: string | null;
  age_tier: string | null;
  risk_score: number;
  timeline: TimelineItem[];
  risk_trend_7d: RiskTrendPoint[];
  risk_trend_30d: RiskTrendPoint[];
  platform_breakdown: PlatformBreakdown[];
  unresolved_alerts: number;
  pending_contact_requests: number;
  flagged_content_count: number;
  degraded_sections: string[];
}

type ScreenState = 'loading' | 'loaded' | 'error';

// ---------------------------------------------------------------------------
// Severity colours
// ---------------------------------------------------------------------------

const SEVERITY_COLOR: Record<string, string> = {
  critical: colors.semantic.error,
  high: colors.semantic.error,
  medium: colors.semantic.warning,
  low: colors.semantic.success,
  info: colors.neutral[500],
};

// Source label mapping
const SOURCE_LABEL: Record<string, string> = {
  ai: 'AI',
  social_post: 'Post',
  social_message: 'Message',
  risk: 'Risk',
  moderation: 'Moderation',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Risk score circle with colour coding */
function RiskScoreBadge({ score }: { score: number }) {
  const color =
    score >= 70
      ? colors.semantic.success
      : score >= 40
        ? colors.semantic.warning
        : colors.semantic.error;

  return React.createElement(
    View,
    { style: styles.scoreBadge, accessibilityLabel: `Safety score ${score}` },
    React.createElement(
      Text,
      { style: [styles.scoreValue, { color }] },
      String(score)
    ),
    React.createElement(Text, { style: styles.scoreLabel }, 'Safety')
  );
}

/** Mini bar chart for risk trend */
function RiskTrendChart({
  data,
  label,
}: {
  data: RiskTrendPoint[];
  label: string;
}) {
  const maxCount = Math.max(1, ...data.map((d) => d.count));

  return React.createElement(
    Card,
    { style: styles.trendCard },
    React.createElement(
      Text,
      { style: styles.sectionTitle, accessibilityRole: 'header' },
      label
    ),
    React.createElement(
      View,
      { style: styles.barContainer, accessibilityLabel: `${label} chart` },
      ...data.map((point) =>
        React.createElement(
          View,
          { key: point.date, style: styles.barWrapper },
          React.createElement(View, {
            style: [
              styles.bar,
              {
                height: Math.max(2, (point.count / maxCount) * 60),
                backgroundColor:
                  point.high_count > 0
                    ? colors.semantic.error
                    : colors.primary[400],
              },
            ],
          })
        )
      )
    )
  );
}

/** Platform breakdown row */
function PlatformRow({ item }: { item: PlatformBreakdown }) {
  return React.createElement(
    View,
    { style: styles.platformRow, accessibilityLabel: `${item.platform} ${item.event_count} events` },
    React.createElement(Text, { style: styles.platformName }, item.platform),
    React.createElement(
      View,
      { style: styles.platformBarBg },
      React.createElement(View, {
        style: [
          styles.platformBarFill,
          { width: `${Math.min(item.percentage, 100)}%` },
        ],
      })
    ),
    React.createElement(
      Text,
      { style: styles.platformPct },
      `${item.percentage.toFixed(0)}%`
    )
  );
}

/** Single timeline entry */
function TimelineEntry({ item }: { item: TimelineItem }) {
  const sevColor = SEVERITY_COLOR[item.severity ?? 'info'] ?? colors.neutral[500];
  const sourceLabel = SOURCE_LABEL[item.source] ?? item.source;

  return React.createElement(
    Card,
    { style: styles.timelineCard },
    React.createElement(
      View,
      { style: styles.timelineHeader },
      React.createElement(Badge, {
        text: sourceLabel,
        variant:
          item.source === 'risk' || item.source === 'moderation'
            ? 'error'
            : item.source === 'ai'
              ? 'info'
              : 'success',
      }),
      item.severity
        ? React.createElement(
            View,
            { style: [styles.sevDot, { backgroundColor: sevColor }] }
          )
        : null,
      React.createElement(
        Text,
        { style: styles.timelineTs },
        new Date(item.timestamp).toLocaleString()
      )
    ),
    React.createElement(
      Text,
      { style: styles.timelineTitle },
      item.title
    ),
    item.detail
      ? React.createElement(
          Text,
          { style: styles.timelineDetail, numberOfLines: 2 },
          item.detail
        )
      : null,
    item.platform
      ? React.createElement(
          Text,
          { style: styles.timelinePlatform },
          item.platform
        )
      : null
  );
}

/** Quick action button row */
function QuickActions({
  unresolved,
  pendingContacts,
  flaggedContent,
}: {
  unresolved: number;
  pendingContacts: number;
  flaggedContent: number;
}) {
  return React.createElement(
    View,
    { style: styles.quickActions },
    React.createElement(
      TouchableOpacity,
      { style: styles.actionBtn, accessibilityLabel: `${unresolved} unresolved alerts` },
      React.createElement(Text, { style: styles.actionCount }, String(unresolved)),
      React.createElement(Text, { style: styles.actionLabel }, 'Alerts')
    ),
    React.createElement(
      TouchableOpacity,
      { style: styles.actionBtn, accessibilityLabel: `${pendingContacts} pending contacts` },
      React.createElement(Text, { style: styles.actionCount }, String(pendingContacts)),
      React.createElement(Text, { style: styles.actionLabel }, 'Contacts')
    ),
    React.createElement(
      TouchableOpacity,
      { style: styles.actionBtn, accessibilityLabel: `${flaggedContent} flagged items` },
      React.createElement(Text, { style: styles.actionCount }, String(flaggedContent)),
      React.createElement(Text, { style: styles.actionLabel }, 'Flagged')
    )
  );
}

// ---------------------------------------------------------------------------
// Main Screen
// ---------------------------------------------------------------------------

export default function ChildProfileScreen() {
  const [data, setData] = useState<ChildProfileData | null>(null);
  const [state, setState] = useState<ScreenState>('loading');
  const [error, setError] = useState('');
  const [trendRange, setTrendRange] = useState<'7d' | '30d'>('7d');

  useEffect(() => {
    loadProfile();
  }, []);

  async function loadProfile() {
    try {
      setState('loading');
      // API call placeholder: GET /api/v1/portal/child-profile?member_id=<id>
      // const response = await apiClient.get<ChildProfileData>(
      //   `/api/v1/portal/child-profile?member_id=${memberId}`
      // );
      // setData(response);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Failed to load child profile.');
    }
  }

  // Loading state
  if (state === 'loading' && !data) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading profile' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  // Error state
  if (state === 'error' && !data) {
    return React.createElement(
      View,
      { style: styles.centered },
      React.createElement(
        Text,
        { style: styles.errorText, accessibilityRole: 'alert' },
        error
      ),
      React.createElement(Button, {
        title: 'Retry',
        onPress: loadProfile,
        variant: 'outline',
      })
    );
  }

  if (!data) {
    return React.createElement(
      View,
      { style: styles.centered },
      React.createElement(Text, { style: styles.emptyText }, 'No profile data available.')
    );
  }

  const trendData = trendRange === '7d' ? data.risk_trend_7d : data.risk_trend_30d;

  return React.createElement(
    ScrollView,
    { style: styles.container, contentContainerStyle: styles.scrollContent },

    // Degraded sections warning
    data.degraded_sections.length > 0
      ? React.createElement(
          View,
          { style: styles.degradedBanner, accessibilityRole: 'alert' },
          React.createElement(
            Text,
            { style: styles.degradedText },
            `Some sections could not load: ${data.degraded_sections.join(', ')}`
          )
        )
      : null,

    // --- Header: Avatar + Name + Age Tier + Risk Score ---
    React.createElement(
      Card,
      { style: styles.headerCard },
      React.createElement(
        View,
        { style: styles.headerRow },
        React.createElement(Avatar, {
          name: data.member_name,
          size: 'lg',
        }),
        React.createElement(
          View,
          { style: styles.headerInfo },
          React.createElement(
            Text,
            { style: styles.memberName, accessibilityRole: 'header' },
            data.member_name
          ),
          data.age_tier
            ? React.createElement(Badge, {
                text: data.age_tier,
                variant: 'info',
              })
            : null
        ),
        React.createElement(RiskScoreBadge, { score: data.risk_score })
      )
    ),

    // --- Quick Actions ---
    React.createElement(QuickActions, {
      unresolved: data.unresolved_alerts,
      pendingContacts: data.pending_contact_requests,
      flaggedContent: data.flagged_content_count,
    }),

    // --- Risk Trend ---
    React.createElement(
      View,
      { style: styles.trendToggle },
      React.createElement(
        TouchableOpacity,
        {
          onPress: () => setTrendRange('7d'),
          style: [styles.toggleBtn, trendRange === '7d' && styles.toggleActive],
          accessibilityLabel: '7 day trend',
        },
        React.createElement(
          Text,
          { style: [styles.toggleText, trendRange === '7d' && styles.toggleTextActive] },
          '7 days'
        )
      ),
      React.createElement(
        TouchableOpacity,
        {
          onPress: () => setTrendRange('30d'),
          style: [styles.toggleBtn, trendRange === '30d' && styles.toggleActive],
          accessibilityLabel: '30 day trend',
        },
        React.createElement(
          Text,
          { style: [styles.toggleText, trendRange === '30d' && styles.toggleTextActive] },
          '30 days'
        )
      )
    ),
    trendData.length > 0
      ? React.createElement(RiskTrendChart, {
          data: trendData,
          label: `Risk Trend (${trendRange})`,
        })
      : null,

    // --- Platform Breakdown ---
    data.platform_breakdown.length > 0
      ? React.createElement(
          Card,
          { style: styles.platformCard },
          React.createElement(
            Text,
            { style: styles.sectionTitle, accessibilityRole: 'header' },
            'Platform Usage'
          ),
          ...data.platform_breakdown.map((pb) =>
            React.createElement(PlatformRow, { key: pb.platform, item: pb })
          )
        )
      : null,

    // --- Unified Timeline ---
    React.createElement(
      Text,
      { style: styles.timelineSectionTitle, accessibilityRole: 'header' },
      'Activity Timeline'
    ),
    data.timeline.length === 0
      ? React.createElement(
          View,
          { style: styles.emptyTimeline },
          React.createElement(
            Text,
            { style: styles.emptyText },
            'No activity recorded yet.'
          )
        )
      : null,
    ...data.timeline.map((item) =>
      React.createElement(TimelineEntry, { key: item.id, item })
    )
  );
}

// Exported for testing
export {
  RiskScoreBadge,
  RiskTrendChart,
  PlatformRow,
  TimelineEntry,
  QuickActions,
  SEVERITY_COLOR,
  SOURCE_LABEL,
};
export type { ChildProfileData, TimelineItem, RiskTrendPoint, PlatformBreakdown, ScreenState };

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  scrollContent: {
    padding: spacing.md,
    paddingBottom: spacing['2xl'],
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.neutral[50],
  },
  degradedBanner: {
    backgroundColor: '#FEF3C7',
    padding: spacing.sm,
    borderRadius: 8,
    marginBottom: spacing.md,
  },
  degradedText: {
    color: '#92400E',
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
  },
  headerCard: {
    marginBottom: spacing.md,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerInfo: {
    flex: 1,
    marginLeft: spacing.md,
  },
  memberName: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    marginBottom: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  scoreBadge: {
    alignItems: 'center',
    marginLeft: spacing.sm,
  },
  scoreValue: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
  scoreLabel: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  quickActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: spacing.md,
  },
  actionBtn: {
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    minHeight: 44,
    justifyContent: 'center',
  },
  actionCount: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.primary[700],
    fontFamily: typography.fontFamily,
  },
  actionLabel: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  trendToggle: {
    flexDirection: 'row',
    marginBottom: spacing.sm,
  },
  toggleBtn: {
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.md,
    borderRadius: 16,
    marginRight: spacing.sm,
    backgroundColor: colors.neutral[200],
    minHeight: 44,
    justifyContent: 'center',
  },
  toggleActive: {
    backgroundColor: colors.primary[600],
  },
  toggleText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
  },
  toggleTextActive: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  trendCard: {
    marginBottom: spacing.md,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[900],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  barContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    height: 70,
    gap: 2,
  },
  barWrapper: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'flex-end',
  },
  bar: {
    width: '80%',
    borderRadius: 2,
    minHeight: 2,
  },
  platformCard: {
    marginBottom: spacing.md,
  },
  platformRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  platformName: {
    width: 100,
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
  },
  platformBarBg: {
    flex: 1,
    height: 8,
    backgroundColor: colors.neutral[200],
    borderRadius: 4,
    overflow: 'hidden',
    marginHorizontal: spacing.sm,
  },
  platformBarFill: {
    height: '100%',
    backgroundColor: colors.primary[500],
    borderRadius: 4,
  },
  platformPct: {
    width: 40,
    textAlign: 'right',
    fontSize: typography.sizes.sm,
    color: colors.neutral[600],
    fontFamily: typography.fontFamily,
  },
  timelineSectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[900],
    marginTop: spacing.sm,
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  timelineCard: {
    marginBottom: spacing.sm,
  },
  timelineHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  sevDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginLeft: spacing.xs,
  },
  timelineTs: {
    flex: 1,
    textAlign: 'right',
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  timelineTitle: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  timelineDetail: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[600],
    marginTop: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  timelinePlatform: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[400],
    marginTop: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  emptyTimeline: {
    paddingVertical: spacing.xl,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    textAlign: 'center',
    fontFamily: typography.fontFamily,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    textAlign: 'center',
    padding: spacing.md,
    fontFamily: typography.fontFamily,
  },
});
