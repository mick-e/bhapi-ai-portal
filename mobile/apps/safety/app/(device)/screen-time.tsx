/**
 * Screen Time Screen
 *
 * Shows: daily/weekly screen time chart, app breakdown, category breakdown.
 * API: GET /api/v1/device/screen-time (single day)
 *      GET /api/v1/device/screen-time/range (date range)
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
import { Card } from '@bhapi/ui';

type ScreenTimeSummary = {
  id: string;
  member_id: string;
  date: string;
  total_minutes: number;
  app_breakdown: Record<string, number> | null;
  category_breakdown: Record<string, number> | null;
  pickups: number;
};

type ViewMode = 'daily' | 'weekly';
type ScreenState = 'loading' | 'loaded' | 'error';

function formatMinutes(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  if (hours === 0) return `${mins}m`;
  if (mins === 0) return `${hours}h`;
  return `${hours}h ${mins}m`;
}

function getBarWidth(value: number, max: number): number {
  if (max === 0) return 0;
  return Math.min((value / max) * 100, 100);
}

const CATEGORY_COLORS: Record<string, string> = {
  social: colors.primary[500],
  education: colors.teal[500],
  games: colors.amber[500],
  entertainment: colors.purple[500],
  productivity: colors.blue[500],
  other: colors.neutral[400],
};

export default function ScreenTimeScreen() {
  const [state, setState] = useState<ScreenState>('loading');
  const [viewMode, setViewMode] = useState<ViewMode>('daily');
  const [todaySummary, setTodaySummary] = useState<ScreenTimeSummary | null>(null);
  const [weeklySummaries, setWeeklySummaries] = useState<ScreenTimeSummary[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, [viewMode]);

  async function loadData() {
    try {
      setState('loading');
      // if (viewMode === 'daily') {
      //   const resp = await apiClient.get('/api/v1/device/screen-time', { params: { member_id, target_date: today } });
      //   setTodaySummary(resp);
      // } else {
      //   const resp = await apiClient.get('/api/v1/device/screen-time/range', { params: { member_id, start_date, end_date } });
      //   setWeeklySummaries(resp.items);
      // }
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Failed to load screen time data.');
    }
  }

  async function onRefresh() {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  }

  if (state === 'loading' && !refreshing) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary[600]} />
        <Text style={styles.loadingText}>Loading screen time...</Text>
      </View>
    );
  }

  if (state === 'error') {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <Text style={styles.title}>Screen Time</Text>

      {/* View mode toggle */}
      <View style={styles.toggleRow}>
        <TouchableOpacity
          style={[styles.toggleBtn, viewMode === 'daily' && styles.toggleActive]}
          onPress={() => setViewMode('daily')}
        >
          <Text
            style={[
              styles.toggleText,
              viewMode === 'daily' && styles.toggleTextActive,
            ]}
          >
            Today
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.toggleBtn, viewMode === 'weekly' && styles.toggleActive]}
          onPress={() => setViewMode('weekly')}
        >
          <Text
            style={[
              styles.toggleText,
              viewMode === 'weekly' && styles.toggleTextActive,
            ]}
          >
            This Week
          </Text>
        </TouchableOpacity>
      </View>

      {viewMode === 'daily' && todaySummary && (
        <>
          {/* Total time card */}
          <Card style={styles.totalCard}>
            <Text style={styles.totalLabel}>Total Screen Time</Text>
            <Text style={styles.totalValue}>
              {formatMinutes(todaySummary.total_minutes)}
            </Text>
            <Text style={styles.pickups}>
              {todaySummary.pickups} pickup{todaySummary.pickups !== 1 ? 's' : ''}
            </Text>
          </Card>

          {/* Category breakdown */}
          {todaySummary.category_breakdown && (
            <Card style={styles.breakdownCard}>
              <Text style={styles.sectionTitle}>By Category</Text>
              {Object.entries(todaySummary.category_breakdown)
                .sort(([, a], [, b]) => b - a)
                .map(([category, minutes]) => (
                  <View key={category} style={styles.barRow}>
                    <Text style={styles.barLabel}>{category}</Text>
                    <View style={styles.barTrack}>
                      <View
                        style={[
                          styles.barFill,
                          {
                            width: `${getBarWidth(minutes, todaySummary.total_minutes)}%`,
                            backgroundColor:
                              CATEGORY_COLORS[category] ?? colors.neutral[400],
                          },
                        ]}
                      />
                    </View>
                    <Text style={styles.barValue}>{formatMinutes(minutes)}</Text>
                  </View>
                ))}
            </Card>
          )}

          {/* App breakdown */}
          {todaySummary.app_breakdown && (
            <Card style={styles.breakdownCard}>
              <Text style={styles.sectionTitle}>By App</Text>
              {Object.entries(todaySummary.app_breakdown)
                .sort(([, a], [, b]) => b - a)
                .map(([app, minutes]) => (
                  <View key={app} style={styles.barRow}>
                    <Text style={styles.barLabel}>{app}</Text>
                    <View style={styles.barTrack}>
                      <View
                        style={[
                          styles.barFill,
                          {
                            width: `${getBarWidth(minutes, todaySummary.total_minutes)}%`,
                            backgroundColor: colors.primary[500],
                          },
                        ]}
                      />
                    </View>
                    <Text style={styles.barValue}>{formatMinutes(minutes)}</Text>
                  </View>
                ))}
            </Card>
          )}
        </>
      )}

      {viewMode === 'weekly' && weeklySummaries.length > 0 && (
        <Card style={styles.weeklyCard}>
          <Text style={styles.sectionTitle}>Daily Totals</Text>
          {weeklySummaries.map((day) => (
            <View key={day.date} style={styles.dayRow}>
              <Text style={styles.dayLabel}>
                {new Date(day.date + 'T00:00:00').toLocaleDateString(undefined, {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                })}
              </Text>
              <View style={styles.barTrack}>
                <View
                  style={[
                    styles.barFill,
                    {
                      width: `${getBarWidth(
                        day.total_minutes,
                        Math.max(...weeklySummaries.map((d) => d.total_minutes), 1),
                      )}%`,
                      backgroundColor: colors.primary[500],
                    },
                  ]}
                />
              </View>
              <Text style={styles.barValue}>
                {formatMinutes(day.total_minutes)}
              </Text>
            </View>
          ))}
        </Card>
      )}

      {viewMode === 'daily' && !todaySummary && (
        <Card style={styles.emptyCard}>
          <Text style={styles.emptyText}>
            No screen time data for today yet. Data will appear once the device
            agent syncs.
          </Text>
        </Card>
      )}

      {viewMode === 'weekly' && weeklySummaries.length === 0 && (
        <Card style={styles.emptyCard}>
          <Text style={styles.emptyText}>
            No screen time data for this week yet.
          </Text>
        </Card>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
    padding: spacing[4],
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing[4],
  },
  title: {
    fontSize: typography.fontSize['2xl'],
    fontWeight: '700' as const,
    color: colors.neutral[900],
    marginBottom: spacing[4],
  },
  loadingText: {
    marginTop: spacing[2],
    color: colors.neutral[500],
  },
  errorText: {
    color: colors.red[600],
    textAlign: 'center' as const,
  },
  toggleRow: {
    flexDirection: 'row' as const,
    marginBottom: spacing[4],
    backgroundColor: colors.neutral[200],
    borderRadius: 8,
    padding: 2,
  },
  toggleBtn: {
    flex: 1,
    paddingVertical: spacing[2],
    alignItems: 'center' as const,
    borderRadius: 6,
  },
  toggleActive: {
    backgroundColor: colors.white,
  },
  toggleText: {
    fontSize: typography.fontSize.sm,
    color: colors.neutral[500],
    fontWeight: '500' as const,
  },
  toggleTextActive: {
    color: colors.primary[700],
    fontWeight: '600' as const,
  },
  totalCard: {
    padding: spacing[5],
    alignItems: 'center' as const,
    marginBottom: spacing[4],
  },
  totalLabel: {
    fontSize: typography.fontSize.sm,
    color: colors.neutral[500],
    marginBottom: spacing[1],
  },
  totalValue: {
    fontSize: 36,
    fontWeight: '700' as const,
    color: colors.neutral[900],
  },
  pickups: {
    fontSize: typography.fontSize.sm,
    color: colors.neutral[400],
    marginTop: spacing[1],
  },
  breakdownCard: {
    padding: spacing[4],
    marginBottom: spacing[4],
  },
  weeklyCard: {
    padding: spacing[4],
    marginBottom: spacing[4],
  },
  sectionTitle: {
    fontSize: typography.fontSize.base,
    fontWeight: '600' as const,
    color: colors.neutral[900],
    marginBottom: spacing[3],
  },
  barRow: {
    flexDirection: 'row' as const,
    alignItems: 'center' as const,
    marginBottom: spacing[2],
  },
  dayRow: {
    flexDirection: 'row' as const,
    alignItems: 'center' as const,
    marginBottom: spacing[2],
  },
  barLabel: {
    width: 90,
    fontSize: typography.fontSize.sm,
    color: colors.neutral[700],
  },
  dayLabel: {
    width: 90,
    fontSize: typography.fontSize.sm,
    color: colors.neutral[700],
  },
  barTrack: {
    flex: 1,
    height: 8,
    backgroundColor: colors.neutral[200],
    borderRadius: 4,
    marginHorizontal: spacing[2],
    overflow: 'hidden' as const,
  },
  barFill: {
    height: '100%',
    borderRadius: 4,
  },
  barValue: {
    width: 55,
    fontSize: typography.fontSize.xs,
    color: colors.neutral[500],
    textAlign: 'right' as const,
  },
  emptyCard: {
    padding: spacing[4],
  },
  emptyText: {
    color: colors.neutral[500],
    textAlign: 'center' as const,
    lineHeight: 22,
  },
});
