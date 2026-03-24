/**
 * Location Dashboard Screen
 *
 * Shows child's current/last-known location on a placeholder map view,
 * geofence overlays (home=green, school=blue, custom=orange),
 * and today's location history timeline with quick actions.
 * API: GET /api/v1/location/history?member_id=<id>&date=<date>
 * API: GET /api/v1/location/geofences?group_id=<id>
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
import { Badge, Button, Card } from '@bhapi/ui';
import type { LocationPoint, Geofence, GeofenceType } from '@bhapi/types';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const GEOFENCE_COLORS: Record<GeofenceType, string> = {
  home: '#16A34A',    // green-600
  school: '#2563EB',  // blue-600
  custom: '#EA580C',  // orange-600
};

export const GEOFENCE_LABELS: Record<GeofenceType, string> = {
  home: 'Home',
  school: 'School',
  custom: 'Custom',
};

export const RETENTION_OPTIONS = [7, 14, 30, 90];

// ---------------------------------------------------------------------------
// Map Placeholder (exported for testing)
// ---------------------------------------------------------------------------

interface MapPlaceholderProps {
  lastPoint: LocationPoint | null;
  geofences: Geofence[];
}

export function MapPlaceholder({ lastPoint, geofences }: MapPlaceholderProps) {
  return React.createElement(
    View,
    {
      style: mapStyles.container,
      accessibilityLabel: 'Location map view',
      accessibilityRole: 'image',
    },
    React.createElement(
      View,
      { style: mapStyles.mapArea },
      React.createElement(
        Text,
        { style: mapStyles.mapEmoji },
        '\uD83D\uDDFA\uFE0F'
      ),
      React.createElement(
        Text,
        { style: mapStyles.mapTitle },
        'Map View'
      ),
      lastPoint
        ? React.createElement(
            Text,
            { style: mapStyles.coordsText },
            `Last seen: ${lastPoint.lat.toFixed(4)}, ${lastPoint.lng.toFixed(4)}`
          )
        : React.createElement(
            Text,
            { style: mapStyles.noLocationText },
            'No location data available'
          ),
      geofences.length > 0
        ? React.createElement(
            View,
            { style: mapStyles.geofencePills },
            ...geofences.map((gf) =>
              React.createElement(
                View,
                {
                  key: gf.id,
                  style: [
                    mapStyles.geofencePill,
                    { backgroundColor: GEOFENCE_COLORS[gf.type] },
                  ],
                },
                React.createElement(
                  Text,
                  { style: mapStyles.geofencePillText },
                  gf.name
                )
              )
            )
          )
        : null
    )
  );
}

const mapStyles = StyleSheet.create({
  container: {
    marginBottom: spacing.md,
  },
  mapArea: {
    backgroundColor: colors.neutral[100],
    borderRadius: 12,
    height: 200,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.neutral[200],
    padding: spacing.md,
    gap: spacing.xs,
  },
  mapEmoji: {
    fontSize: 40,
    lineHeight: 48,
  },
  mapTitle: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[600],
    fontFamily: typography.fontFamily,
  },
  coordsText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  noLocationText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
    fontStyle: 'italic',
  },
  geofencePills: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
    marginTop: spacing.xs,
    justifyContent: 'center',
  },
  geofencePill: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: 12,
  },
  geofencePillText: {
    fontSize: typography.sizes.xs,
    color: '#FFFFFF',
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
});

// ---------------------------------------------------------------------------
// Geofence list item (exported for testing)
// ---------------------------------------------------------------------------

interface GeofenceItemProps {
  geofence: Geofence;
}

export function GeofenceItem({ geofence }: GeofenceItemProps) {
  const color = GEOFENCE_COLORS[geofence.type];
  const label = GEOFENCE_LABELS[geofence.type];

  return React.createElement(
    View,
    {
      style: geofenceStyles.container,
      accessibilityLabel: `Geofence: ${geofence.name}`,
    },
    React.createElement(
      View,
      { style: [geofenceStyles.colorDot, { backgroundColor: color }] }
    ),
    React.createElement(
      View,
      { style: geofenceStyles.info },
      React.createElement(
        Text,
        { style: geofenceStyles.name },
        geofence.name
      ),
      React.createElement(
        Text,
        { style: geofenceStyles.detail },
        `${label} \u00B7 ${geofence.radius_meters}m radius`
      )
    ),
    geofence.alerts_enabled
      ? React.createElement(Badge, { text: 'Alerts on', variant: 'success' })
      : React.createElement(Badge, { text: 'Alerts off', variant: 'info' })
  );
}

const geofenceStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
    minHeight: 52,
    gap: spacing.sm,
  },
  colorDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    flexShrink: 0,
  },
  info: {
    flex: 1,
    gap: 2,
  },
  name: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  detail: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
});

// ---------------------------------------------------------------------------
// History timeline item (exported for testing)
// ---------------------------------------------------------------------------

interface HistoryPointProps {
  point: LocationPoint;
  isFirst?: boolean;
  isLast?: boolean;
}

export function HistoryPoint({ point, isFirst, isLast }: HistoryPointProps) {
  const time = new Date(point.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return React.createElement(
    View,
    {
      style: historyStyles.container,
      accessibilityLabel: `Location at ${time}`,
    },
    React.createElement(
      View,
      { style: historyStyles.timelineCol },
      isFirst ? null : React.createElement(View, { style: historyStyles.lineTop }),
      React.createElement(View, { style: historyStyles.dot }),
      isLast ? null : React.createElement(View, { style: historyStyles.lineBottom })
    ),
    React.createElement(
      View,
      { style: historyStyles.content },
      React.createElement(
        Text,
        { style: historyStyles.time },
        time
      ),
      React.createElement(
        Text,
        { style: historyStyles.coords },
        `${point.lat.toFixed(4)}, ${point.lng.toFixed(4)}`
      ),
      point.accuracy != null
        ? React.createElement(
            Text,
            { style: historyStyles.accuracy },
            `Accuracy: \u00B1${Math.round(point.accuracy)}m`
          )
        : null
    )
  );
}

const historyStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  timelineCol: {
    width: 20,
    alignItems: 'center',
    flexShrink: 0,
  },
  lineTop: {
    width: 2,
    flex: 1,
    backgroundColor: colors.neutral[200],
    marginBottom: 2,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.primary[500],
    borderWidth: 2,
    borderColor: colors.primary[200],
  },
  lineBottom: {
    width: 2,
    flex: 1,
    backgroundColor: colors.neutral[200],
    marginTop: 2,
  },
  content: {
    flex: 1,
    paddingBottom: spacing.sm,
    gap: 2,
  },
  time: {
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  coords: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  accuracy: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
  },
});

// ---------------------------------------------------------------------------
// Main screen
// ---------------------------------------------------------------------------

export default function LocationScreen() {
  const [locationHistory] = useState<LocationPoint[]>([]);
  const [geofences] = useState<Geofence[]>([]);
  const [loading] = useState(false);
  const [error] = useState('');

  // In production, replace with:
  // const { data: historyData, isLoading } = useLocationHistory(childId);
  // const { data: geofenceData } = useGeofences(groupId);
  // setLoading(isLoading)

  const lastPoint = locationHistory.length > 0
    ? locationHistory[locationHistory.length - 1]
    : null;

  if (loading) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading location' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  if (error) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Location error' },
      React.createElement(
        Text,
        { style: styles.errorText, accessibilityRole: 'alert' },
        error
      )
    );
  }

  return React.createElement(
    ScrollView,
    {
      style: styles.container,
      contentContainerStyle: styles.content,
      accessibilityLabel: 'Location',
    },
    React.createElement(
      Text,
      { style: styles.heading, accessibilityRole: 'header' },
      'Location'
    ),

    // Map view
    React.createElement(MapPlaceholder, {
      lastPoint,
      geofences,
    }),

    // Quick actions
    React.createElement(
      View,
      { style: styles.quickActions },
      React.createElement(Button, {
        title: '+ Add Geofence',
        onPress: () => {
          // Navigate to location-settings for geofence management
        },
        variant: 'outline',
        style: styles.actionBtn,
        accessibilityLabel: 'Add geofence',
      }),
      React.createElement(Button, {
        title: 'View History',
        onPress: () => {
          // Navigate to detailed history view
        },
        variant: 'outline',
        style: styles.actionBtn,
        accessibilityLabel: 'View location history',
      })
    ),

    // Geofences card
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Geofences' },
      React.createElement(
        View,
        { style: styles.cardHeader },
        React.createElement(Text, { style: styles.sectionTitle }, 'Geofences'),
        React.createElement(Badge, {
          text: `${geofences.length}`,
          variant: 'info',
        })
      ),
      geofences.length === 0
        ? React.createElement(
            Text,
            { style: styles.emptyText },
            'No geofences set. Add safe zones like Home or School to get arrival/departure alerts.'
          )
        : geofences.map((gf) =>
            React.createElement(GeofenceItem, {
              key: gf.id,
              geofence: gf,
            })
          )
    ),

    // Today's history card
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: "Today's location history" },
      React.createElement(Text, { style: styles.sectionTitle }, "Today's Movements"),
      locationHistory.length === 0
        ? React.createElement(
            Text,
            { style: styles.emptyText },
            'No location data recorded today.'
          )
        : locationHistory.map((point, idx) =>
            React.createElement(HistoryPoint, {
              key: `${point.timestamp}-${idx}`,
              point,
              isFirst: idx === 0,
              isLast: idx === locationHistory.length - 1,
            })
          )
    )
  );
}

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
  quickActions: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  actionBtn: {
    flex: 1,
  },
  card: {
    marginBottom: spacing.md,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  sectionTitle: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  emptyText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
    textAlign: 'center',
    paddingVertical: spacing.sm,
    lineHeight: 20,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.base,
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
});
