/**
 * Device Overview Screen
 *
 * Shows: active devices, recent sessions, battery status.
 * API: GET /api/v1/device/sessions (via member_id query param)
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Card, Badge } from '@bhapi/ui';

type DeviceSession = {
  id: string;
  device_id: string;
  device_type: 'ios' | 'android' | 'tablet';
  os_version: string | null;
  app_version: string | null;
  started_at: string;
  ended_at: string | null;
  battery_level: number | null;
};

type ScreenState = 'loading' | 'loaded' | 'error';

const DEVICE_ICONS: Record<string, string> = {
  ios: 'iPhone',
  android: 'Android',
  tablet: 'Tablet',
};

export default function DeviceOverviewScreen() {
  const [state, setState] = useState<ScreenState>('loading');
  const [sessions, setSessions] = useState<DeviceSession[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSessions();
  }, []);

  async function loadSessions() {
    try {
      setState('loading');
      // API call: GET /api/v1/device/sessions?member_id=...
      // const response = await apiClient.get('/api/v1/device/sessions', { params: { member_id } });
      // setSessions(response.items);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Failed to load device sessions.');
    }
  }

  async function onRefresh() {
    setRefreshing(true);
    await loadSessions();
    setRefreshing(false);
  }

  if (state === 'loading' && !refreshing) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary[600]} />
        <Text style={styles.loadingText}>Loading devices...</Text>
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
      <Text style={styles.title}>Devices</Text>
      <Text style={styles.subtitle}>
        Monitored devices and recent activity
      </Text>

      {sessions.length === 0 ? (
        <Card style={styles.emptyCard}>
          <Text style={styles.emptyText}>
            No device sessions recorded yet. Install the safety agent on your
            child's device to begin monitoring.
          </Text>
        </Card>
      ) : (
        sessions.map((session) => (
          <Card key={session.id} style={styles.sessionCard}>
            <View style={styles.sessionHeader}>
              <Text style={styles.deviceName}>
                {DEVICE_ICONS[session.device_type] ?? session.device_type}
              </Text>
              <Badge
                variant={session.ended_at ? 'info' : 'success'}
                label={session.ended_at ? 'Ended' : 'Active'}
              />
            </View>
            <Text style={styles.detail}>Device: {session.device_id}</Text>
            {session.os_version && (
              <Text style={styles.detail}>OS: {session.os_version}</Text>
            )}
            {session.app_version && (
              <Text style={styles.detail}>App: v{session.app_version}</Text>
            )}
            {session.battery_level != null && (
              <Text style={styles.detail}>
                Battery: {session.battery_level}%
              </Text>
            )}
            <Text style={styles.timestamp}>
              Started: {new Date(session.started_at).toLocaleString()}
            </Text>
          </Card>
        ))
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
    marginBottom: spacing[1],
  },
  subtitle: {
    fontSize: typography.fontSize.sm,
    color: colors.neutral[500],
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
  emptyCard: {
    padding: spacing[4],
  },
  emptyText: {
    color: colors.neutral[500],
    textAlign: 'center' as const,
    lineHeight: 22,
  },
  sessionCard: {
    padding: spacing[4],
    marginBottom: spacing[3],
  },
  sessionHeader: {
    flexDirection: 'row' as const,
    justifyContent: 'space-between' as const,
    alignItems: 'center' as const,
    marginBottom: spacing[2],
  },
  deviceName: {
    fontSize: typography.fontSize.lg,
    fontWeight: '600' as const,
    color: colors.neutral[900],
  },
  detail: {
    fontSize: typography.fontSize.sm,
    color: colors.neutral[600],
    marginBottom: spacing[1],
  },
  timestamp: {
    fontSize: typography.fontSize.xs,
    color: colors.neutral[400],
    marginTop: spacing[2],
  },
});
