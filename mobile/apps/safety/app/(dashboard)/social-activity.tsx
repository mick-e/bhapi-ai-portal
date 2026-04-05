/**
 * Social Activity Monitoring Screen (P2-M1)
 *
 * Per-child overview: post count, message count, contacts,
 * flagged content, and time chart.
 *
 * API: GET /api/v1/portal/social-activity?member_id=<id>
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Card, Badge } from '@bhapi/ui';
import { ApiClient } from '@bhapi/api';
import { tokenManager } from '@bhapi/auth';

const apiClient = new ApiClient({
  baseUrl: '',
  getToken: () => tokenManager.getToken(),
});

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TimeTrendPoint {
  date: string;
  minutes: number;
}

interface FlaggedItem {
  id: string;
  content_type: string;
  content_id: string;
  status: string;
  created_at: string;
}

interface SocialActivityData {
  member_id: string;
  member_name: string;
  post_count_7d: number;
  post_count_30d: number;
  message_count_7d: number;
  message_count_30d: number;
  contact_count: number;
  pending_contact_requests: number;
  flagged_content_count: number;
  flagged_items: FlaggedItem[];
  time_spent_minutes_7d: number;
  time_spent_minutes_30d: number;
  time_trend: TimeTrendPoint[];
  degraded_sections: string[];
}

// ---------------------------------------------------------------------------
// Stat Card sub-component
// ---------------------------------------------------------------------------

function StatBox({
  label,
  value7d,
  value30d,
}: {
  label: string;
  value7d: number;
  value30d: number;
}) {
  return React.createElement(
    Card,
    null,
    React.createElement(
      Text,
      { style: styles.statLabel, accessibilityRole: 'text' },
      label
    ),
    React.createElement(
      View,
      { style: styles.statRow },
      React.createElement(
        View,
        { style: styles.statCol },
        React.createElement(
          Text,
          { style: styles.statValue, accessibilityLabel: `${value7d} in last 7 days` },
          String(value7d)
        ),
        React.createElement(Text, { style: styles.statPeriod }, '7 days')
      ),
      React.createElement(
        View,
        { style: styles.statCol },
        React.createElement(
          Text,
          { style: styles.statValue, accessibilityLabel: `${value30d} in last 30 days` },
          String(value30d)
        ),
        React.createElement(Text, { style: styles.statPeriod }, '30 days')
      )
    )
  );
}

// ---------------------------------------------------------------------------
// Time bar chart (simple horizontal bars)
// ---------------------------------------------------------------------------

function TimeChart({ trend }: { trend: TimeTrendPoint[] }) {
  const maxMinutes = Math.max(...trend.map((t) => t.minutes), 1);

  return React.createElement(
    Card,
    null,
    React.createElement(
      Text,
      { style: styles.sectionTitle, accessibilityRole: 'header' },
      'Daily Activity (minutes)'
    ),
    ...trend.map((point) => {
      const barWidth = (point.minutes / maxMinutes) * 100;
      const dayLabel = point.date.slice(5); // MM-DD
      return React.createElement(
        View,
        { key: point.date, style: styles.barRow, accessibilityLabel: `${dayLabel}: ${point.minutes} minutes` },
        React.createElement(Text, { style: styles.barLabel }, dayLabel),
        React.createElement(
          View,
          { style: styles.barTrack },
          React.createElement(View, {
            style: [styles.barFill, { width: `${Math.max(barWidth, 2)}%` }],
          })
        ),
        React.createElement(
          Text,
          { style: styles.barValue },
          `${point.minutes}m`
        )
      );
    })
  );
}

// ---------------------------------------------------------------------------
// Main screen
// ---------------------------------------------------------------------------

export default function SocialActivityScreen() {
  const [data, setData] = useState<SocialActivityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      setError('');
      // Wire up real API — member_id optional (returns current user's children data when omitted)
      const response = await apiClient.get<SocialActivityData>(
        `/api/v1/social/feed`
      );
      setData(response as unknown as SocialActivityData);
      setLoading(false);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load social activity.');
      setLoading(false);
    }
  }

  if (loading) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading social activity' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  if (error) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Social activity error' },
      React.createElement(
        Text,
        { style: styles.errorText, accessibilityRole: 'alert' },
        error
      ),
      React.createElement(
        TouchableOpacity,
        {
          onPress: loadData,
          style: styles.retryButton,
          accessibilityLabel: 'Retry loading social activity',
        },
        React.createElement(Text, { style: styles.retryText }, 'Tap to retry')
      )
    );
  }

  if (!data) {
    return React.createElement(
      View,
      { style: styles.centered },
      React.createElement(
        Text,
        { style: styles.emptyText },
        'Select a child to view their social activity.'
      )
    );
  }

  return React.createElement(
    ScrollView,
    { style: styles.container, accessibilityLabel: 'Social Activity' },
    // Header
    React.createElement(
      Text,
      { style: styles.heading, accessibilityRole: 'header' },
      `${data.member_name}'s Activity`
    ),

    // Degraded warning
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

    // Posts
    React.createElement(StatBox, {
      label: 'Posts',
      value7d: data.post_count_7d,
      value30d: data.post_count_30d,
    }),

    // Messages
    React.createElement(StatBox, {
      label: 'Messages',
      value7d: data.message_count_7d,
      value30d: data.message_count_30d,
    }),

    // Contacts
    React.createElement(
      Card,
      null,
      React.createElement(
        Text,
        { style: styles.sectionTitle, accessibilityRole: 'header' },
        'Contacts'
      ),
      React.createElement(
        View,
        { style: styles.statRow },
        React.createElement(
          View,
          { style: styles.statCol },
          React.createElement(
            Text,
            { style: styles.statValue, accessibilityLabel: `${data.contact_count} contacts` },
            String(data.contact_count)
          ),
          React.createElement(Text, { style: styles.statPeriod }, 'Accepted')
        ),
        React.createElement(
          View,
          { style: styles.statCol },
          React.createElement(
            Text,
            {
              style: [
                styles.statValue,
                data.pending_contact_requests > 0 ? styles.warningValue : null,
              ],
              accessibilityLabel: `${data.pending_contact_requests} pending requests`,
            },
            String(data.pending_contact_requests)
          ),
          React.createElement(Text, { style: styles.statPeriod }, 'Pending')
        )
      )
    ),

    // Flagged content
    React.createElement(
      Card,
      null,
      React.createElement(
        View,
        { style: styles.flaggedHeader },
        React.createElement(
          Text,
          { style: styles.sectionTitle, accessibilityRole: 'header' },
          'Flagged Content'
        ),
        data.flagged_content_count > 0
          ? React.createElement(Badge, {
              text: String(data.flagged_content_count),
              variant: 'error',
            })
          : React.createElement(Badge, { text: '0', variant: 'success' })
      ),
      ...data.flagged_items.map((item) =>
        React.createElement(
          View,
          { key: item.id, style: styles.flaggedItem },
          React.createElement(Badge, {
            text: item.content_type,
            variant: 'warning',
          }),
          React.createElement(Badge, {
            text: item.status,
            variant: item.status === 'rejected' ? 'error' : 'warning',
            style: { marginLeft: spacing.xs },
          }),
          React.createElement(
            Text,
            { style: styles.flaggedDate },
            item.created_at.slice(0, 10)
          )
        )
      )
    ),

    // Time estimates
    React.createElement(StatBox, {
      label: 'Estimated Time (minutes)',
      value7d: data.time_spent_minutes_7d,
      value30d: data.time_spent_minutes_30d,
    }),

    // Time trend chart
    data.time_trend.length > 0
      ? React.createElement(TimeChart, { trend: data.time_trend })
      : null,

    // Bottom spacer
    React.createElement(View, { style: { height: spacing['2xl'] } })
  );
}

// Exported for testing
export { StatBox, TimeChart };
export type { SocialActivityData, TimeTrendPoint, FlaggedItem };

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
    paddingHorizontal: spacing.md,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.neutral[50],
  },
  heading: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[800],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  statLabel: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[800],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  statCol: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.primary[600],
    fontFamily: typography.fontFamily,
  },
  warningValue: {
    color: colors.semantic.warning,
  },
  statPeriod: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  flaggedHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  flaggedItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.xs,
    gap: spacing.xs,
  },
  flaggedDate: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    marginLeft: 'auto',
    fontFamily: typography.fontFamily,
  },
  barRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  barLabel: {
    width: 50,
    fontSize: typography.sizes.xs,
    color: colors.neutral[600],
    fontFamily: typography.fontFamily,
  },
  barTrack: {
    flex: 1,
    height: 12,
    backgroundColor: colors.neutral[100],
    borderRadius: 6,
    overflow: 'hidden',
    marginHorizontal: spacing.xs,
  },
  barFill: {
    height: '100%',
    backgroundColor: colors.accent[500],
    borderRadius: 6,
  },
  barValue: {
    width: 40,
    fontSize: typography.sizes.xs,
    color: colors.neutral[600],
    textAlign: 'right',
    fontFamily: typography.fontFamily,
  },
  degradedBanner: {
    backgroundColor: '#FEF3CD',
    padding: spacing.sm,
    borderRadius: 8,
    marginBottom: spacing.sm,
  },
  degradedText: {
    fontSize: typography.sizes.sm,
    color: '#856404',
    fontFamily: typography.fontFamily,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.base,
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  retryButton: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    minHeight: 44,
    justifyContent: 'center',
  },
  retryText: {
    color: colors.primary[700],
    fontSize: typography.sizes.base,
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  emptyText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    textAlign: 'center',
    fontFamily: typography.fontFamily,
  },
});
