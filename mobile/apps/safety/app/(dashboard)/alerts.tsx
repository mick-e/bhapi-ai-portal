/**
 * Alerts List Screen
 *
 * Filterable list of alerts with severity badges.
 * API: GET /api/v1/alerts?severity=<filter>&status=<filter>&page=<n>
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
import type { Alert, AlertSeverity, AlertStatus } from '@bhapi/types';

type FilterSeverity = AlertSeverity | 'all';

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

export default function AlertsScreen() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<FilterSeverity>('all');
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadAlerts();
  }, [filter]);

  async function loadAlerts() {
    try {
      setLoading(true);
      setError('');
      // API call: GET /api/v1/alerts?severity=<filter>
      // const params = filter !== 'all' ? `?severity=${filter}` : '';
      // const response = await apiClient.get<PagedResponse<Alert>>(`/api/v1/alerts${params}`);
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

  function renderFilterBar() {
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
              filter === f.value ? styles.filterChipActive : null,
            ],
            onPress: () => setFilter(f.value),
            accessibilityRole: 'tab',
            accessibilityState: { selected: filter === f.value },
            accessibilityLabel: `Filter by ${f.label}`,
          },
          React.createElement(
            Text,
            {
              style: [
                styles.filterText,
                filter === f.value ? styles.filterTextActive : null,
              ],
            },
            f.label
          )
        )
      )
    );
  }

  function renderAlert({ item }: { item: Alert }) {
    return React.createElement(
      TouchableOpacity,
      {
        style: styles.alertItem,
        accessibilityLabel: `${item.severity} alert: ${item.title}`,
        // onPress: () => router.push({ pathname: '/(dashboard)/alert-detail', params: { id: item.id } }),
      },
      React.createElement(
        Card,
        null,
        React.createElement(
          View,
          { style: styles.alertHeader },
          React.createElement(Badge, {
            text: item.severity,
            variant: SEVERITY_VARIANT[item.severity],
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
    { style: styles.container, accessibilityLabel: 'Alerts' },
    React.createElement(
      Text,
      { style: styles.heading, accessibilityRole: 'header' },
      'Alerts'
    ),
    renderFilterBar(),
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
          filter === 'all'
            ? 'No alerts yet. Everything looks safe!'
            : `No ${filter} alerts.`
        )
      ),
    })
  );
}

// Exported for testing
export { SEVERITY_FILTERS, SEVERITY_VARIANT, type FilterSeverity };

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
