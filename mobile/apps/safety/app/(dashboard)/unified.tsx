/**
 * Unified Parent Dashboard Screen
 *
 * Aggregates risk score, AI activity, social activity, screen time,
 * location, and action center into a single scrollable view with
 * pull-to-refresh.
 *
 * API endpoints (parallel fetch):
 *   GET /api/v1/risk/score?member_id=<id>
 *   GET /api/v1/capture/events?member_id=<id>&page_size=5
 *   GET /api/v1/social/summary?member_id=<id>
 *   GET /api/v1/screen-time/summary?member_id=<id>
 *   GET /api/v1/location/last?member_id=<id>
 *   GET /api/v1/alerts?read=false&page_size=1
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Card, Badge, RiskScoreCard } from '@bhapi/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

interface RiskScoreData {
  score: number;
  trend: 'up' | 'down' | 'stable';
  confidence: 'low' | 'medium' | 'high';
  factors: string[];
}

interface AIActivityData {
  events_today: number;
  top_platforms: string[];
}

interface SocialData {
  posts_today: number;
  comments_today: number;
  friend_requests_pending: number;
}

interface ScreenTimeData {
  total_minutes_today: number;
  top_categories: Array<{ category: string; minutes: number }>;
}

interface LocationData {
  last_known_location: string | null;
  geofence_status: 'inside' | 'outside' | 'unknown';
  last_updated: string | null;
}

interface ActionCenterData {
  pending_approvals: number;
  unread_alerts: number;
  pending_extension_requests: number;
}

interface UnifiedData {
  riskScore: RiskScoreData | null;
  aiActivity: AIActivityData | null;
  social: SocialData | null;
  screenTime: ScreenTimeData | null;
  location: LocationData | null;
  actionCenter: ActionCenterData | null;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

interface SectionHeaderProps {
  title: string;
}

export function SectionHeader({ title }: SectionHeaderProps) {
  return React.createElement(
    Text,
    { style: styles.sectionTitle, accessibilityRole: 'header' },
    title
  );
}

interface StatRowProps {
  label: string;
  value: string | number;
}

export function StatRow({ label, value }: StatRowProps) {
  return React.createElement(
    View,
    { style: styles.statRow, accessibilityLabel: `${label}: ${value}` },
    React.createElement(Text, { style: styles.statLabel }, label),
    React.createElement(Text, { style: styles.statValue }, String(value))
  );
}

interface ActionItemRowProps {
  label: string;
  count: number;
  urgentThreshold?: number;
}

export function ActionItemRow({ label, count, urgentThreshold = 1 }: ActionItemRowProps) {
  const isUrgent = count >= urgentThreshold;
  const badgeVariant: 'error' | 'warning' | 'info' =
    count === 0 ? 'info' : isUrgent ? 'error' : 'warning';

  return React.createElement(
    View,
    { style: styles.actionItemRow, accessibilityLabel: `${label}: ${count}` },
    React.createElement(Text, { style: styles.actionItemLabel }, label),
    React.createElement(Badge, { text: String(count), variant: badgeVariant })
  );
}

// ─── Screen ───────────────────────────────────────────────────────────────────

type ScreenState = 'loading' | 'loaded' | 'error';

export default function UnifiedDashboardScreen() {
  const [state, setState] = useState<ScreenState>('loading');
  const [data, setData] = useState<UnifiedData>({
    riskScore: null,
    aiActivity: null,
    social: null,
    screenTime: null,
    location: null,
    actionCenter: null,
  });
  const [refreshing, setRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const loadDashboard = useCallback(async () => {
    try {
      setState('loading');
      // Parallel fetches — each is optional (null on failure)
      // In production replace with real apiClient calls:
      // const [riskScore, activityResp, social, screenTime, location, alerts] =
      //   await Promise.allSettled([
      //     apiClient.get('/api/v1/risk/score?member_id=' + memberId),
      //     apiClient.get('/api/v1/capture/events?member_id=' + memberId + '&page_size=5'),
      //     apiClient.get('/api/v1/social/summary?member_id=' + memberId),
      //     apiClient.get('/api/v1/screen-time/summary?member_id=' + memberId),
      //     apiClient.get('/api/v1/location/last?member_id=' + memberId),
      //     apiClient.get('/api/v1/alerts?read=false&page_size=1'),
      //   ]);
      setData({
        riskScore: null,
        aiActivity: null,
        social: null,
        screenTime: null,
        location: null,
        actionCenter: null,
      });
      setState('loaded');
    } catch (e: unknown) {
      setState('error');
      setErrorMessage(
        e instanceof Error ? e.message : 'Failed to load dashboard.'
      );
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadDashboard();
    setRefreshing(false);
  }, [loadDashboard]);

  if (state === 'loading' && !refreshing) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading unified dashboard' },
      React.createElement(ActivityIndicator, { size: 'large', color: colors.primary[600] })
    );
  }

  if (state === 'error') {
    return React.createElement(
      View,
      { style: styles.centered },
      React.createElement(
        Text,
        { style: styles.errorText, accessibilityRole: 'alert' },
        errorMessage
      ),
      React.createElement(
        TouchableOpacity,
        {
          onPress: loadDashboard,
          style: styles.retryButton,
          accessibilityLabel: 'Retry loading dashboard',
        },
        React.createElement(Text, { style: styles.retryText }, 'Tap to retry')
      )
    );
  }

  const { riskScore, aiActivity, social, screenTime, location, actionCenter } = data;

  return React.createElement(
    ScrollView,
    {
      style: styles.container,
      contentContainerStyle: styles.content,
      refreshControl: React.createElement(RefreshControl, {
        refreshing,
        onRefresh: handleRefresh,
        tintColor: colors.primary[600],
      }),
      accessibilityLabel: 'Unified Dashboard',
    },

    // Page heading
    React.createElement(
      Text,
      { style: styles.heading, accessibilityRole: 'header' },
      'Unified Dashboard'
    ),

    // ── Risk Score ──────────────────────────────────────────────────────────
    React.createElement(SectionHeader, { title: 'Risk Score' }),
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Risk score card' },
      riskScore
        ? React.createElement(RiskScoreCard, {
            score: riskScore.score,
            trend: riskScore.trend,
            confidence: riskScore.confidence,
            factors: riskScore.factors,
          })
        : React.createElement(
            Text,
            { style: styles.emptyText },
            'No risk data available yet.'
          )
    ),

    // ── AI Activity ─────────────────────────────────────────────────────────
    React.createElement(SectionHeader, { title: 'AI Activity' }),
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'AI activity card' },
      aiActivity
        ? React.createElement(
            View,
            null,
            React.createElement(StatRow, {
              label: 'Events today',
              value: aiActivity.events_today,
            }),
            aiActivity.top_platforms.length > 0
              ? React.createElement(
                  View,
                  { style: styles.platformRow },
                  aiActivity.top_platforms.map((p) =>
                    React.createElement(Badge, {
                      key: p,
                      text: p,
                      variant: 'info',
                      style: { marginRight: spacing.xs },
                    })
                  )
                )
              : null
          )
        : React.createElement(
            Text,
            { style: styles.emptyText },
            'No AI activity data available.'
          )
    ),

    // ── Social Activity ─────────────────────────────────────────────────────
    React.createElement(SectionHeader, { title: 'Social Activity' }),
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Social activity card' },
      social
        ? React.createElement(
            View,
            null,
            React.createElement(StatRow, { label: 'Posts today', value: social.posts_today }),
            React.createElement(StatRow, { label: 'Comments today', value: social.comments_today }),
            React.createElement(StatRow, {
              label: 'Pending friend requests',
              value: social.friend_requests_pending,
            })
          )
        : React.createElement(
            Text,
            { style: styles.emptyText },
            'No social data available.'
          )
    ),

    // ── Screen Time ─────────────────────────────────────────────────────────
    React.createElement(SectionHeader, { title: 'Screen Time' }),
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Screen time card' },
      screenTime
        ? React.createElement(
            View,
            null,
            React.createElement(StatRow, {
              label: 'Total today',
              value: `${Math.floor(screenTime.total_minutes_today / 60)}h ${screenTime.total_minutes_today % 60}m`,
            }),
            ...screenTime.top_categories.slice(0, 3).map((c) =>
              React.createElement(StatRow, {
                key: c.category,
                label: c.category,
                value: `${c.minutes}m`,
              })
            )
          )
        : React.createElement(
            Text,
            { style: styles.emptyText },
            'No screen time data available.'
          )
    ),

    // ── Location ────────────────────────────────────────────────────────────
    React.createElement(SectionHeader, { title: 'Location' }),
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Location card' },
      location
        ? React.createElement(
            View,
            null,
            React.createElement(StatRow, {
              label: 'Last known location',
              value: location.last_known_location ?? 'Unavailable',
            }),
            React.createElement(
              View,
              { style: styles.geofenceRow },
              React.createElement(
                Text,
                { style: styles.statLabel },
                'Geofence status'
              ),
              React.createElement(Badge, {
                text:
                  location.geofence_status === 'inside'
                    ? 'Inside safe zone'
                    : location.geofence_status === 'outside'
                    ? 'Outside safe zone'
                    : 'Unknown',
                variant:
                  location.geofence_status === 'inside'
                    ? 'success'
                    : location.geofence_status === 'outside'
                    ? 'error'
                    : 'info',
              })
            )
          )
        : React.createElement(
            Text,
            { style: styles.emptyText },
            'No location data available.'
          )
    ),

    // ── Action Center ───────────────────────────────────────────────────────
    React.createElement(SectionHeader, { title: 'Action Center' }),
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Action center card' },
      actionCenter
        ? React.createElement(
            View,
            null,
            React.createElement(ActionItemRow, {
              label: 'Pending approvals',
              count: actionCenter.pending_approvals,
              urgentThreshold: 1,
            }),
            React.createElement(ActionItemRow, {
              label: 'Unread alerts',
              count: actionCenter.unread_alerts,
              urgentThreshold: 3,
            }),
            React.createElement(ActionItemRow, {
              label: 'Extension requests',
              count: actionCenter.pending_extension_requests,
              urgentThreshold: 1,
            })
          )
        : React.createElement(
            Text,
            { style: styles.emptyText },
            'No action items.'
          )
    )
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

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
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[900],
    marginTop: spacing.md,
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  card: {
    marginBottom: spacing.sm,
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
  },
  statLabel: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[600],
    fontFamily: typography.fontFamily,
  },
  statValue: {
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  platformRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: spacing.sm,
  },
  geofenceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  actionItemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
  },
  actionItemLabel: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
  },
  emptyText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
    fontStyle: 'italic',
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
});

export { type UnifiedData, type RiskScoreData, type ActionCenterData };
