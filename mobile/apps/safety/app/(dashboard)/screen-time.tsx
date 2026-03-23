/**
 * Screen Time Dashboard Screen
 *
 * Shows today's usage summary (total minutes, per-category bars),
 * active rules with usage percentage indicators, pending extension
 * requests with approve/deny actions, and weekly trend (daily totals).
 *
 * API: GET /api/v1/screen-time/evaluate?member_id=<id>
 * API: GET /api/v1/screen-time/extensions?member_id=<id>&status=pending
 * API: GET /api/v1/screen-time/weekly-report?member_id=<id>
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Badge, Card } from '@bhapi/ui';
import type {
  UsageEvaluation,
  ExtensionRequest,
  WeeklyReport,
  DailyTotal,
  EnforcementAction,
} from '@bhapi/types';

// ---------------------------------------------------------------------------
// Sub-components (exported for testing)
// ---------------------------------------------------------------------------

interface UsageBarProps {
  label: string;
  usedMinutes: number;
  limitMinutes: number;
  percent: number;
  enforcement: EnforcementAction;
}

export function UsageBar({ label, usedMinutes, limitMinutes, percent, enforcement }: UsageBarProps) {
  const clampedPercent = Math.min(percent, 100);
  const isOver = percent >= 100;
  const isWarning = percent >= 80 && !isOver;

  const barColor = isOver
    ? colors.semantic.error
    : isWarning
    ? colors.semantic.warning
    : colors.primary[500];

  return React.createElement(
    View,
    { style: usageBarStyles.container, accessibilityLabel: `${label}: ${usedMinutes} of ${limitMinutes} minutes used` },
    React.createElement(
      View,
      { style: usageBarStyles.header },
      React.createElement(Text, { style: usageBarStyles.label }, label),
      React.createElement(
        Text,
        { style: [usageBarStyles.minutes, isOver ? usageBarStyles.minutesOver : null] },
        `${usedMinutes}m / ${limitMinutes}m`
      )
    ),
    React.createElement(
      View,
      { style: usageBarStyles.track },
      React.createElement(View, {
        style: [
          usageBarStyles.fill,
          { width: `${clampedPercent}%` as any, backgroundColor: barColor },
        ],
        accessibilityLabel: `${Math.round(clampedPercent)}% used`,
      })
    ),
    enforcement === 'hard_block' && isOver
      ? React.createElement(
          Text,
          { style: usageBarStyles.enforcementText },
          'Blocked'
        )
      : null
  );
}

const usageBarStyles = StyleSheet.create({
  container: {
    marginBottom: spacing.sm,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  label: {
    fontSize: typography.sizes.sm,
    fontWeight: '500',
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
    textTransform: 'capitalize',
  },
  minutes: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  minutesOver: {
    color: colors.semantic.error,
    fontWeight: '600',
  },
  track: {
    height: 8,
    backgroundColor: colors.neutral[200],
    borderRadius: 4,
    overflow: 'hidden',
  },
  fill: {
    height: 8,
    borderRadius: 4,
  },
  enforcementText: {
    fontSize: typography.sizes.xs,
    color: colors.semantic.error,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
    marginTop: 2,
  },
});

// ---------------------------------------------------------------------------
// Extension request card (exported for testing)
// ---------------------------------------------------------------------------

interface ExtensionCardProps {
  request: ExtensionRequest;
  onApprove: (id: string) => void;
  onDeny: (id: string) => void;
  loading?: boolean;
}

export function ExtensionCard({ request, onApprove, onDeny, loading }: ExtensionCardProps) {
  return React.createElement(
    Card,
    { style: extCardStyles.card, accessibilityLabel: `Extension request: ${request.requested_minutes} minutes` },
    React.createElement(
      View,
      { style: extCardStyles.header },
      React.createElement(
        Text,
        { style: extCardStyles.title },
        `+${request.requested_minutes} min requested`
      ),
      React.createElement(Badge, {
        text: 'Pending',
        variant: 'warning',
      })
    ),
    request.reason
      ? React.createElement(
          Text,
          { style: extCardStyles.reason, numberOfLines: 2 },
          request.reason
        )
      : null,
    React.createElement(
      Text,
      { style: extCardStyles.meta },
      `Requested ${new Date(request.requested_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
    ),
    React.createElement(
      View,
      { style: extCardStyles.actions },
      React.createElement(
        TouchableOpacity,
        {
          style: [extCardStyles.actionBtn, extCardStyles.denyBtn],
          onPress: () => onDeny(request.id),
          disabled: loading,
          accessibilityLabel: 'Deny extension request',
          accessibilityRole: 'button',
        },
        React.createElement(Text, { style: extCardStyles.denyText }, 'Deny')
      ),
      React.createElement(
        TouchableOpacity,
        {
          style: [extCardStyles.actionBtn, extCardStyles.approveBtn],
          onPress: () => onApprove(request.id),
          disabled: loading,
          accessibilityLabel: 'Approve extension request',
          accessibilityRole: 'button',
        },
        React.createElement(Text, { style: extCardStyles.approveText }, 'Approve')
      )
    )
  );
}

const extCardStyles = StyleSheet.create({
  card: {
    marginBottom: spacing.sm,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  title: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  reason: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[600],
    fontFamily: typography.fontFamily,
    marginBottom: spacing.xs,
  },
  meta: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
    marginBottom: spacing.sm,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  actionBtn: {
    flex: 1,
    paddingVertical: spacing.sm,
    borderRadius: 8,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  approveBtn: {
    backgroundColor: colors.primary[600],
  },
  approveText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  denyBtn: {
    backgroundColor: colors.neutral[100],
  },
  denyText: {
    color: colors.neutral[700],
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
});

// ---------------------------------------------------------------------------
// Weekly trend bar (exported for testing)
// ---------------------------------------------------------------------------

interface WeeklyTrendProps {
  report: WeeklyReport;
}

export function WeeklyTrend({ report }: WeeklyTrendProps) {
  const maxMinutes = Math.max(...report.daily_totals.map((d) => d.minutes), 1);

  return React.createElement(
    View,
    { style: trendStyles.container, accessibilityLabel: 'Weekly screen time trend' },
    React.createElement(
      View,
      { style: trendStyles.bars },
      ...report.daily_totals.map((day: DailyTotal) => {
        const heightPercent = (day.minutes / maxMinutes) * 100;
        const dayLabel = new Date(day.date).toLocaleDateString('en', { weekday: 'short' });
        return React.createElement(
          View,
          { key: day.date, style: trendStyles.barCol },
          React.createElement(
            View,
            { style: trendStyles.barTrack },
            React.createElement(View, {
              style: [
                trendStyles.barFill,
                { height: `${heightPercent}%` as any },
              ],
              accessibilityLabel: `${dayLabel}: ${day.minutes} minutes`,
            })
          ),
          React.createElement(
            Text,
            { style: trendStyles.dayLabel },
            dayLabel
          )
        );
      })
    ),
    React.createElement(
      View,
      { style: trendStyles.summary },
      React.createElement(
        Text,
        { style: trendStyles.summaryText },
        `Avg ${Math.round(report.daily_average_minutes)} min/day`
      ),
      React.createElement(
        Text,
        { style: trendStyles.summaryText },
        `Total ${report.total_minutes} min this week`
      )
    )
  );
}

const trendStyles = StyleSheet.create({
  container: {
    marginTop: spacing.xs,
  },
  bars: {
    flexDirection: 'row',
    height: 80,
    gap: spacing.xs,
    alignItems: 'flex-end',
  },
  barCol: {
    flex: 1,
    alignItems: 'center',
    height: '100%',
    justifyContent: 'flex-end',
  },
  barTrack: {
    flex: 1,
    width: '100%',
    justifyContent: 'flex-end',
  },
  barFill: {
    width: '100%',
    backgroundColor: colors.primary[400],
    borderRadius: 3,
    minHeight: 2,
  },
  dayLabel: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
    marginTop: 4,
  },
  summary: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.sm,
  },
  summaryText: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
});

// ---------------------------------------------------------------------------
// Main Screen
// ---------------------------------------------------------------------------

// Demo child/group IDs — in production these come from navigation params or
// the selected child context.
const DEMO_CHILD_ID = '';
const DEMO_GROUP_ID = '';

type ScreenState = 'loading' | 'loaded' | 'error';

export default function ScreenTimeDashboard() {
  const [usage, setUsage] = useState<UsageEvaluation[]>([]);
  const [extensions, setExtensions] = useState<ExtensionRequest[]>([]);
  const [weeklyReport, setWeeklyReport] = useState<WeeklyReport | null>(null);
  const [screenState, setScreenState] = useState<ScreenState>('loaded');
  const [error, setError] = useState('');
  const [respondingId, setRespondingId] = useState<string | null>(null);

  // In production, load via useUsageEvaluation / useExtensionRequests / useWeeklyReport hooks.
  // Hooks are defined in src/hooks/useScreenTime.ts and connect to /api/v1/screen-time/*.
  // For the shell: data is empty by default; loading handled inline.

  const totalMinutesToday = usage.reduce((sum, u) => sum + u.used_minutes, 0);

  async function handleApprove(requestId: string) {
    setRespondingId(requestId);
    try {
      // await respondExtension({ requestId, action: 'approve' });
      setExtensions((prev) => prev.filter((r) => r.id !== requestId));
    } catch (e: any) {
      setError(e?.message ?? 'Failed to approve request.');
    } finally {
      setRespondingId(null);
    }
  }

  async function handleDeny(requestId: string) {
    setRespondingId(requestId);
    try {
      // await respondExtension({ requestId, action: 'deny' });
      setExtensions((prev) => prev.filter((r) => r.id !== requestId));
    } catch (e: any) {
      setError(e?.message ?? 'Failed to deny request.');
    } finally {
      setRespondingId(null);
    }
  }

  if (screenState === 'loading') {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading screen time data' },
      React.createElement(ActivityIndicator, { size: 'large', color: colors.primary[600] })
    );
  }

  if (screenState === 'error') {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Screen time error' },
      React.createElement(
        Text,
        { style: styles.errorText, accessibilityRole: 'alert' },
        error || 'Failed to load screen time data.'
      ),
      React.createElement(
        TouchableOpacity,
        {
          style: styles.retryButton,
          onPress: () => setScreenState('loading'),
          accessibilityLabel: 'Retry loading screen time',
        },
        React.createElement(Text, { style: styles.retryText }, 'Tap to retry')
      )
    );
  }

  return React.createElement(
    ScrollView,
    {
      style: styles.container,
      contentContainerStyle: styles.content,
      accessibilityLabel: 'Screen Time Dashboard',
    },
    // Header
    React.createElement(
      Text,
      { style: styles.heading, accessibilityRole: 'header' },
      'Screen Time'
    ),

    // Today's usage summary
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: "Today's usage summary" },
      React.createElement(Text, { style: styles.sectionTitle }, "Today's Usage"),
      React.createElement(
        View,
        { style: styles.totalRow },
        React.createElement(
          Text,
          { style: styles.totalMinutes },
          `${totalMinutesToday} min`
        ),
        React.createElement(
          Text,
          { style: styles.totalLabel },
          'total today'
        )
      ),
      usage.length === 0
        ? React.createElement(
            Text,
            { style: styles.emptyText },
            'No usage data yet for today.'
          )
        : usage.map((u: UsageEvaluation) =>
            React.createElement(UsageBar, {
              key: u.rule_id,
              label: u.category,
              usedMinutes: u.used_minutes,
              limitMinutes: u.limit_minutes,
              percent: u.percent,
              enforcement: u.enforcement_action,
            })
          )
    ),

    // Extension requests
    React.createElement(
      View,
      { style: styles.sectionHeader },
      React.createElement(
        Text,
        { style: styles.sectionHeading },
        'Extension Requests'
      ),
      extensions.length > 0
        ? React.createElement(Badge, {
            text: String(extensions.length),
            variant: 'warning',
          })
        : null
    ),
    extensions.length === 0
      ? React.createElement(
          Text,
          { style: styles.emptySubText },
          'No pending extension requests.'
        )
      : extensions.map((req: ExtensionRequest) =>
          React.createElement(ExtensionCard, {
            key: req.id,
            request: req,
            onApprove: handleApprove,
            onDeny: handleDeny,
            loading: respondingId === req.id,
          })
        ),

    // Weekly trend
    weeklyReport
      ? React.createElement(
          Card,
          { style: styles.card, accessibilityLabel: 'Weekly screen time trend' },
          React.createElement(Text, { style: styles.sectionTitle }, '7-Day Trend'),
          React.createElement(WeeklyTrend, { report: weeklyReport })
        )
      : React.createElement(
          Card,
          { style: styles.card },
          React.createElement(Text, { style: styles.sectionTitle }, '7-Day Trend'),
          React.createElement(
            Text,
            { style: styles.emptyText },
            'No weekly data available yet.'
          )
        ),

    // Global error banner
    error
      ? React.createElement(
          Text,
          { style: styles.errorText, accessibilityRole: 'alert' },
          error
        )
      : null
  );
}

// Exported for testing
export {
  DEMO_CHILD_ID,
  DEMO_GROUP_ID,
  type ScreenState,
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  content: {
    padding: spacing.md,
    paddingBottom: spacing['2xl'],
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
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  card: {
    marginBottom: spacing.md,
  },
  sectionTitle: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    marginBottom: spacing.sm,
  },
  sectionHeading: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  totalRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: spacing.xs,
    marginBottom: spacing.sm,
  },
  totalMinutes: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.primary[600],
    fontFamily: typography.fontFamily,
  },
  totalLabel: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  emptyText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
  },
  emptySubText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
    marginBottom: spacing.md,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    textAlign: 'center',
    marginTop: spacing.sm,
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
});
