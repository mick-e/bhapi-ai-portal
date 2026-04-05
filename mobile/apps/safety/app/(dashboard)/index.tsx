/**
 * Safety Dashboard Screen
 *
 * Shows: activity summary card, risk overview, recent alerts list.
 * API: GET /api/v1/portal/dashboard
 * Response: DashboardData { activity_summary, risk_overview, recent_alerts, ... }
 *
 * Handles degraded_sections from the backend (amber warning when sections fail).
 */
import React, { useState, useEffect } from 'react';
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
import { Card, Badge, MobileEmptyState } from '@bhapi/ui';
import type {
  DashboardData,
  ActivitySummary,
  RiskOverview,
  Alert,
  AlertSeverity,
} from '@bhapi/types';
import { ApiClient } from '@bhapi/api';
import { tokenManager } from '@bhapi/auth';

const apiClient = new ApiClient({
  baseUrl: '',
  getToken: () => tokenManager.getToken(),
});

type DashboardState = 'loading' | 'loaded' | 'error';

const SEVERITY_VARIANT: Record<AlertSeverity, 'info' | 'success' | 'warning' | 'error'> = {
  low: 'info',
  medium: 'warning',
  high: 'error',
  critical: 'error',
};

export default function DashboardScreen() {
  const [state, setState] = useState<DashboardState>('loading');
  const [data, setData] = useState<DashboardData | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      setState('loading');
      const response = await apiClient.get<DashboardData>('/api/v1/portal/dashboard');
      setData(response);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setErrorMessage(e?.message ?? 'Failed to load dashboard.');
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    await loadDashboard();
    setRefreshing(false);
  }

  if (state === 'loading' && !data) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading dashboard' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  if (state === 'error' && !data) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Dashboard error' },
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
        React.createElement(
          Text,
          { style: styles.retryText },
          'Tap to retry'
        )
      )
    );
  }

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
      accessibilityLabel: 'Dashboard',
    },
    React.createElement(
      Text,
      { style: styles.heading, accessibilityRole: 'header' },
      'Dashboard'
    ),

    // Degraded sections warning
    data?.degraded_sections && data.degraded_sections.length > 0
      ? React.createElement(
          Card,
          {
            style: styles.warningCard,
            accessibilityLabel: 'Some sections are temporarily unavailable',
          },
          React.createElement(
            Text,
            { style: styles.warningText },
            `Some data may be incomplete: ${data.degraded_sections.join(', ')}`
          )
        )
      : null,

    // Activity summary card
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Activity summary' },
      React.createElement(
        Text,
        { style: styles.cardTitle },
        'Activity Summary'
      ),
      React.createElement(
        View,
        { style: styles.statsRow },
        renderStat('Sessions', data?.activity_summary?.total_sessions ?? 0),
        renderStat('Minutes', data?.activity_summary?.total_duration_minutes ?? 0),
        renderStat('Platforms', data?.activity_summary?.platforms_used ?? 0)
      )
    ),

    // Risk overview card
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Risk overview' },
      React.createElement(
        Text,
        { style: styles.cardTitle },
        'Risk Overview'
      ),
      React.createElement(
        View,
        { style: styles.riskRow },
        React.createElement(
          View,
          { style: styles.scoreContainer },
          React.createElement(
            Text,
            { style: styles.scoreValue },
            String(data?.risk_overview?.overall_score ?? '--')
          ),
          React.createElement(
            Text,
            { style: styles.scoreLabel },
            'Safety Score'
          )
        ),
        React.createElement(
          View,
          { style: styles.trendContainer },
          React.createElement(Badge, {
            text: data?.risk_overview?.trend ?? 'stable',
            variant: data?.risk_overview?.trend === 'improving'
              ? 'success'
              : data?.risk_overview?.trend === 'declining'
                ? 'error'
                : 'info',
          }),
          React.createElement(
            Text,
            { style: styles.highRiskCount },
            `${data?.risk_overview?.high_risk_events ?? 0} high risk events`
          )
        )
      )
    ),

    // Recent alerts
    React.createElement(
      Text,
      { style: styles.sectionTitle },
      'Recent Alerts'
    ),
    ...(data?.recent_alerts ?? []).slice(0, 5).map((alert: Alert) =>
      React.createElement(
        TouchableOpacity,
        {
          key: alert.id,
          accessibilityLabel: `Alert: ${alert.title}`,
          // onPress: () => router.push({ pathname: '/(dashboard)/alert-detail', params: { id: alert.id } }),
        },
        React.createElement(
          Card,
          { style: styles.alertCard },
          React.createElement(
            View,
            { style: styles.alertHeader },
            React.createElement(Badge, {
              text: alert.severity,
              variant: SEVERITY_VARIANT[alert.severity],
            }),
            React.createElement(
              Text,
              { style: styles.alertTime },
              alert.created_at
            )
          ),
          React.createElement(
            Text,
            { style: styles.alertTitle },
            alert.title
          ),
          React.createElement(
            Text,
            { style: styles.alertDescription, numberOfLines: 2 },
            alert.description
          )
        )
      )
    ),
    (data?.recent_alerts ?? []).length === 0
      ? React.createElement(MobileEmptyState, {
          title: 'All clear',
          message: "Your family is safe — no alerts this week.",
        })
      : null
  );
}

function renderStat(label: string, value: number) {
  return React.createElement(
    View,
    { key: label, style: styles.statItem, accessibilityLabel: `${label}: ${value}` },
    React.createElement(
      Text,
      { style: styles.statValue },
      String(value)
    ),
    React.createElement(
      Text,
      { style: styles.statLabel },
      label
    )
  );
}

// Exported for testing
export { SEVERITY_VARIANT, type DashboardState };

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
  warningCard: {
    marginBottom: spacing.md,
    backgroundColor: '#FEF3C7',
    borderLeftWidth: 4,
    borderLeftColor: colors.semantic.warning,
  },
  warningText: {
    color: '#92400E',
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
  },
  cardTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[900],
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.primary[600],
    fontFamily: typography.fontFamily,
  },
  statLabel: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    marginTop: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  riskRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  scoreContainer: {
    alignItems: 'center',
  },
  scoreValue: {
    fontSize: typography.sizes['3xl'],
    fontWeight: '700',
    color: colors.accent[500],
    fontFamily: typography.fontFamily,
  },
  scoreLabel: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  trendContainer: {
    alignItems: 'flex-end',
  },
  highRiskCount: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    marginTop: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[900],
    marginBottom: spacing.sm,
    marginTop: spacing.md,
    fontFamily: typography.fontFamily,
  },
  alertCard: {
    marginBottom: spacing.sm,
  },
  alertHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  alertTitle: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    marginBottom: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  alertDescription: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
    lineHeight: 20,
  },
  alertTime: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  emptyText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    textAlign: 'center',
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
});
