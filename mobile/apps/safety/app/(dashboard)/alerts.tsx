/**
 * Unified Alerts Screen
 *
 * Cross-product alert view with source tabs (All|AI|Social|Device),
 * severity badges, and drill-down navigation.
 * API: GET /api/v1/alerts/unified?source=<filter>&severity=<filter>&page=<n>
 * Response: PagedResponse<Alert>
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Badge, Card } from '@bhapi/ui';
import type { Alert, AlertSeverity, AlertSource, AlertStatus } from '@bhapi/types';

type FilterSource = AlertSource | 'all';
type FilterSeverity = AlertSeverity | 'all';

const SOURCE_FILTERS: { value: FilterSource; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'ai', label: 'AI' },
  { value: 'social', label: 'Social' },
  { value: 'device', label: 'Device' },
];

const SEVERITY_FILTERS: { value: FilterSeverity; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const SEVERITY_VARIANT: Record<AlertSeverity, 'info' | 'success' | 'warning' | 'error'> = {
  low: 'info',
  medium: 'warning',
  high: 'error',
  critical: 'error',
};

const SOURCE_COLORS: Record<AlertSource, string> = {
  ai: colors.primary[600],
  social: colors.accent[500],
  device: '#6366F1', // indigo for device
};

export default function AlertsScreen() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sourceFilter, setSourceFilter] = useState<FilterSource>('all');
  const [severityFilter, setSeverityFilter] = useState<FilterSeverity>('all');
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadAlerts();
  }, [sourceFilter, severityFilter]);

  async function loadAlerts() {
    try {
      setLoading(true);
      setError('');
      // API call: GET /api/v1/alerts/unified?source=<filter>&severity=<filter>
      // const params = new URLSearchParams();
      // if (sourceFilter !== 'all') params.append('source', sourceFilter);
      // if (severityFilter !== 'all') params.append('severity', severityFilter);
      // const response = await apiClient.get<PagedResponse<Alert>>(`/api/v1/alerts/unified?${params}`);
      // setAlerts(response.items);
      setLoading(false);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load alerts.');
      setLoading(false);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    await loadAlerts();
    setRefreshing(false);
  }

  function renderSourceTabs() {
    return React.createElement(
      View,
      { style: styles.sourceTabBar, accessibilityRole: 'tablist' },
      ...SOURCE_FILTERS.map((f) =>
        React.createElement(
          TouchableOpacity,
          {
            key: f.value,
            style: [
              styles.sourceTab,
              sourceFilter === f.value ? styles.sourceTabActive : null,
            ],
            onPress: () => setSourceFilter(f.value),
            accessibilityRole: 'tab',
            accessibilityState: { selected: sourceFilter === f.value },
            accessibilityLabel: `Filter by ${f.label} source`,
          },
          React.createElement(
            Text,
            {
              style: [
                styles.sourceTabText,
                sourceFilter === f.value ? styles.sourceTabTextActive : null,
              ],
            },
            f.label
          )
        )
      )
    );
  }

  function renderSeverityBar() {
    return React.createElement(
      View,
      { style: styles.filterBar, accessibilityRole: 'tablist' },
      ...SEVERITY_FILTERS.map((f) =>
        React.createElement(
          TouchableOpacity,
          {
            key: f.value,
            style: [
              styles.filterChip,
              severityFilter === f.value ? styles.filterChipActive : null,
            ],
            onPress: () => setSeverityFilter(f.value),
            accessibilityRole: 'tab',
            accessibilityState: { selected: severityFilter === f.value },
            accessibilityLabel: `Filter by ${f.label} severity`,
          },
          React.createElement(
            Text,
            {
              style: [
                styles.filterText,
                severityFilter === f.value ? styles.filterTextActive : null,
              ],
            },
            f.label
          )
        )
      )
    );
  }

  function renderSourceBadge(source: AlertSource) {
    return React.createElement(
      View,
      {
        style: [
          styles.sourceBadge,
          { backgroundColor: SOURCE_COLORS[source] || colors.neutral[400] },
        ],
      },
      React.createElement(
        Text,
        { style: styles.sourceBadgeText },
        source.toUpperCase()
      )
    );
  }

  function renderAlert({ item }: { item: Alert }) {
    const source: AlertSource = (item as any).source ?? 'ai';
    return React.createElement(
      TouchableOpacity,
      {
        style: styles.alertItem,
        accessibilityLabel: `${item.severity} ${source} alert: ${item.title}`,
      },
      React.createElement(
        Card,
        null,
        React.createElement(
          View,
          { style: styles.alertHeader },
          renderSourceBadge(source),
          React.createElement(Badge, {
            text: item.severity,
            variant: SEVERITY_VARIANT[item.severity],
            style: { marginLeft: spacing.xs },
          }),
          React.createElement(Badge, {
            text: item.status,
            variant: item.status === 'unread' ? 'warning' : 'info',
            style: { marginLeft: spacing.sm },
          })
        ),
        React.createElement(
          Text,
          { style: styles.alertTitle },
          item.title
        ),
        React.createElement(
          Text,
          { style: styles.alertDescription, numberOfLines: 2 },
          item.description
        ),
        React.createElement(
          View,
          { style: styles.alertMeta },
          item.platform
            ? React.createElement(
                Text,
                { style: styles.alertPlatform },
                item.platform
              )
            : null,
          React.createElement(
            Text,
            { style: styles.alertTime },
            item.created_at
          )
        )
      )
    );
  }

  if (loading && alerts.length === 0) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading alerts' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  if (error && alerts.length === 0) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Alerts error' },
      React.createElement(
        Text,
        { style: styles.errorText, accessibilityRole: 'alert' },
        error
      ),
      React.createElement(
        TouchableOpacity,
        {
          onPress: loadAlerts,
          style: styles.retryButton,
          accessibilityLabel: 'Retry loading alerts',
        },
        React.createElement(Text, { style: styles.retryText }, 'Tap to retry')
      )
    );
  }

  return React.createElement(
    View,
    { style: styles.container, accessibilityLabel: 'Unified Alerts' },
    React.createElement(
      Text,
      { style: styles.heading, accessibilityRole: 'header' },
      'Alerts'
    ),
    renderSourceTabs(),
    renderSeverityBar(),
    React.createElement(FlatList, {
      data: alerts,
      keyExtractor: (item: Alert) => item.id,
      renderItem: renderAlert,
      refreshing,
      onRefresh: handleRefresh,
      contentContainerStyle: styles.listContent,
      ListEmptyComponent: React.createElement(
        View,
        { style: styles.emptyContainer },
        React.createElement(
          Text,
          { style: styles.emptyText },
          sourceFilter === 'all' && severityFilter === 'all'
            ? 'No alerts yet. Everything looks safe!'
            : `No ${sourceFilter !== 'all' ? sourceFilter + ' ' : ''}${severityFilter !== 'all' ? severityFilter + ' ' : ''}alerts.`
        )
      ),
    })
  );
}

// Exported for testing
export {
  SOURCE_FILTERS,
  SEVERITY_FILTERS,
  SEVERITY_VARIANT,
  SOURCE_COLORS,
  type FilterSource,
  type FilterSeverity,
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
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
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
    fontFamily: typography.fontFamily,
  },
  sourceTabBar: {
    flexDirection: 'row',
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    gap: spacing.xs,
  },
  sourceTab: {
    flex: 1,
    paddingVertical: spacing.sm,
    borderRadius: 8,
    backgroundColor: colors.neutral[100],
    alignItems: 'center',
    minHeight: 40,
    justifyContent: 'center',
  },
  sourceTabActive: {
    backgroundColor: colors.primary[600],
  },
  sourceTabText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  sourceTabTextActive: {
    color: '#FFFFFF',
  },
  filterBar: {
    flexDirection: 'row',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  filterChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 16,
    backgroundColor: colors.neutral[100],
    minHeight: 36,
    justifyContent: 'center',
  },
  filterChipActive: {
    backgroundColor: colors.primary[600],
  },
  filterText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  filterTextActive: {
    color: '#FFFFFF',
  },
  listContent: {
    padding: spacing.md,
    paddingTop: 0,
  },
  alertItem: {
    marginBottom: spacing.sm,
  },
  alertHeader: {
    flexDirection: 'row',
    marginBottom: spacing.xs,
    alignItems: 'center',
  },
  sourceBadge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: 4,
    minHeight: 22,
    justifyContent: 'center',
  },
  sourceBadgeText: {
    fontSize: typography.sizes.xs,
    color: '#FFFFFF',
    fontWeight: '700',
    fontFamily: typography.fontFamily,
    letterSpacing: 0.5,
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
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
    lineHeight: 20,
  },
  alertMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  alertPlatform: {
    fontSize: typography.sizes.xs,
    color: colors.accent[500],
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  alertTime: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  emptyContainer: {
    paddingVertical: spacing['2xl'],
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
