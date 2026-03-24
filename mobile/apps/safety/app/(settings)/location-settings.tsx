/**
 * Location Settings Screen
 *
 * Toggle tracking on/off, history retention slider (7/14/30/90 days),
 * geofence management (list, add, delete), and emergency kill switch.
 * API: GET/PUT /api/v1/location/settings?member_id=<id>
 * API: GET/POST/DELETE /api/v1/location/geofences?group_id=<id>
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Switch,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Badge, Button, Card } from '@bhapi/ui';
import type { Geofence, GeofenceType } from '@bhapi/types';

// ---------------------------------------------------------------------------
// Constants (exported for testing)
// ---------------------------------------------------------------------------

export const RETENTION_OPTIONS: { value: number; label: string }[] = [
  { value: 7, label: '7 days' },
  { value: 14, label: '14 days' },
  { value: 30, label: '30 days' },
  { value: 90, label: '90 days' },
];

export const GEOFENCE_TYPE_OPTIONS: { value: GeofenceType; label: string; color: string }[] = [
  { value: 'home', label: 'Home', color: '#16A34A' },
  { value: 'school', label: 'School', color: '#2563EB' },
  { value: 'custom', label: 'Custom', color: '#EA580C' },
];

export const DEFAULT_RADIUS_OPTIONS = [100, 200, 500, 1000];

// ---------------------------------------------------------------------------
// Geofence list item (exported for testing)
// ---------------------------------------------------------------------------

interface GeofenceSettingsItemProps {
  geofence: Geofence;
  onDelete: (id: string) => void;
  deleting?: boolean;
}

export function GeofenceSettingsItem({ geofence, onDelete, deleting }: GeofenceSettingsItemProps) {
  const typeOption = GEOFENCE_TYPE_OPTIONS.find((t) => t.value === geofence.type);
  const color = typeOption?.color ?? '#6B7280';

  return React.createElement(
    View,
    {
      style: itemStyles.container,
      accessibilityLabel: `Geofence: ${geofence.name}`,
    },
    React.createElement(
      View,
      { style: [itemStyles.colorDot, { backgroundColor: color }] }
    ),
    React.createElement(
      View,
      { style: itemStyles.info },
      React.createElement(
        Text,
        { style: itemStyles.name },
        geofence.name
      ),
      React.createElement(
        Text,
        { style: itemStyles.detail },
        `${typeOption?.label ?? geofence.type} \u00B7 ${geofence.radius_meters}m`
      )
    ),
    geofence.alerts_enabled
      ? React.createElement(Badge, { text: 'Alerts', variant: 'success' })
      : null,
    React.createElement(
      TouchableOpacity,
      {
        onPress: () => onDelete(geofence.id),
        disabled: deleting,
        style: itemStyles.deleteBtn,
        accessibilityLabel: `Delete geofence ${geofence.name}`,
        accessibilityRole: 'button',
      },
      React.createElement(
        Text,
        { style: itemStyles.deleteText },
        deleting ? '...' : 'Delete'
      )
    )
  );
}

const itemStyles = StyleSheet.create({
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
  deleteBtn: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    minHeight: 36,
    justifyContent: 'center',
  },
  deleteText: {
    fontSize: typography.sizes.sm,
    color: colors.semantic.error,
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
});

// ---------------------------------------------------------------------------
// Add geofence form (exported for testing)
// ---------------------------------------------------------------------------

interface AddGeofenceFormProps {
  onSubmit: (name: string, type: GeofenceType, radiusMeters: number, alertsEnabled: boolean) => void;
  onCancel: () => void;
  loading?: boolean;
}

export function AddGeofenceForm({ onSubmit, onCancel, loading }: AddGeofenceFormProps) {
  const [name, setName] = useState('');
  const [selectedType, setSelectedType] = useState<GeofenceType>('home');
  const [radius, setRadius] = useState(200);
  const [alertsEnabled, setAlertsEnabled] = useState(true);

  // Simple inline name input simulation (RN TextInput would be used in production)
  const NAME_PRESETS = ['Home', 'School', 'Grandma\'s', 'Sports Center', 'Library'];

  return React.createElement(
    View,
    { style: addFormStyles.container, accessibilityLabel: 'Add geofence form' },

    // Name presets
    React.createElement(Text, { style: addFormStyles.label }, 'Name'),
    React.createElement(
      View,
      { style: addFormStyles.row },
      ...NAME_PRESETS.map((preset) =>
        React.createElement(
          TouchableOpacity,
          {
            key: preset,
            style: [
              addFormStyles.chip,
              name === preset ? addFormStyles.chipActive : null,
            ],
            onPress: () => setName(preset),
            accessibilityRole: 'radio',
            accessibilityState: { selected: name === preset },
            accessibilityLabel: preset,
          },
          React.createElement(
            Text,
            {
              style: [
                addFormStyles.chipText,
                name === preset ? addFormStyles.chipTextActive : null,
              ],
            },
            preset
          )
        )
      )
    ),

    // Type selector
    React.createElement(Text, { style: addFormStyles.label }, 'Type'),
    React.createElement(
      View,
      { style: addFormStyles.row },
      ...GEOFENCE_TYPE_OPTIONS.map((opt) =>
        React.createElement(
          TouchableOpacity,
          {
            key: opt.value,
            style: [
              addFormStyles.typeChip,
              selectedType === opt.value
                ? { ...addFormStyles.chipActive, backgroundColor: opt.color }
                : null,
            ],
            onPress: () => setSelectedType(opt.value),
            accessibilityRole: 'radio',
            accessibilityState: { selected: selectedType === opt.value },
            accessibilityLabel: opt.label,
          },
          React.createElement(
            Text,
            {
              style: [
                addFormStyles.chipText,
                selectedType === opt.value ? addFormStyles.chipTextActive : null,
              ],
            },
            opt.label
          )
        )
      )
    ),

    // Radius selector
    React.createElement(Text, { style: addFormStyles.label }, 'Radius'),
    React.createElement(
      View,
      { style: addFormStyles.row },
      ...DEFAULT_RADIUS_OPTIONS.map((r) =>
        React.createElement(
          TouchableOpacity,
          {
            key: r,
            style: [
              addFormStyles.chip,
              radius === r ? addFormStyles.chipActive : null,
            ],
            onPress: () => setRadius(r),
            accessibilityRole: 'radio',
            accessibilityState: { selected: radius === r },
            accessibilityLabel: `${r} meters`,
          },
          React.createElement(
            Text,
            {
              style: [
                addFormStyles.chipText,
                radius === r ? addFormStyles.chipTextActive : null,
              ],
            },
            r >= 1000 ? `${r / 1000}km` : `${r}m`
          )
        )
      )
    ),

    // Alerts toggle
    React.createElement(
      View,
      { style: addFormStyles.switchRow },
      React.createElement(Text, { style: addFormStyles.switchLabel }, 'Enable arrival/departure alerts'),
      React.createElement(Switch, {
        value: alertsEnabled,
        onValueChange: setAlertsEnabled,
        trackColor: { true: colors.primary[500], false: colors.neutral[200] },
        thumbColor: '#FFFFFF',
        accessibilityLabel: 'Enable geofence alerts',
      })
    ),

    // Actions
    React.createElement(
      View,
      { style: addFormStyles.actions },
      React.createElement(
        TouchableOpacity,
        {
          style: addFormStyles.cancelBtn,
          onPress: onCancel,
          accessibilityLabel: 'Cancel',
        },
        React.createElement(Text, { style: addFormStyles.cancelText }, 'Cancel')
      ),
      React.createElement(Button, {
        title: loading ? 'Saving...' : 'Add Geofence',
        onPress: () =>
          onSubmit(name || selectedType, selectedType, radius, alertsEnabled),
        variant: 'primary',
        style: addFormStyles.submitBtn,
        accessibilityLabel: 'Add geofence',
      })
    )
  );
}

const addFormStyles = StyleSheet.create({
  container: {
    padding: spacing.md,
  },
  label: {
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
    marginBottom: spacing.xs,
    marginTop: spacing.sm,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
  },
  chip: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: 16,
    backgroundColor: colors.neutral[100],
    minHeight: 36,
    justifyContent: 'center',
  },
  typeChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 16,
    backgroundColor: colors.neutral[100],
    minHeight: 36,
    justifyContent: 'center',
  },
  chipActive: {
    backgroundColor: colors.primary[600],
  },
  chipText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
    fontWeight: '500',
  },
  chipTextActive: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.md,
    minHeight: 44,
  },
  switchLabel: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
    flex: 1,
    marginRight: spacing.sm,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  cancelBtn: {
    flex: 1,
    paddingVertical: spacing.sm,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  cancelText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[600],
    fontFamily: typography.fontFamily,
  },
  submitBtn: {
    flex: 2,
  },
});

// ---------------------------------------------------------------------------
// Main settings screen
// ---------------------------------------------------------------------------

type SettingsView = 'list' | 'add';

export default function LocationSettings() {
  const [trackingEnabled, setTrackingEnabled] = useState(true);
  const [retentionDays, setRetentionDays] = useState(30);
  const [geofences, setGeofences] = useState<Geofence[]>([]);
  const [view, setView] = useState<SettingsView>('list');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [addingGeofence, setAddingGeofence] = useState(false);
  const [error, setError] = useState('');

  // In production, replace with:
  // const { data: settings } = useLocationSettings(childId);
  // const { mutateAsync: updateSettings } = useUpdateLocationSettings();
  // const { data: geofencesData } = useGeofences(groupId);
  // const { mutateAsync: createGeofence } = useCreateGeofence();
  // const { mutateAsync: deleteGeofence } = useDeleteGeofence();

  async function handleToggleTracking(value: boolean) {
    setTrackingEnabled(value);
    try {
      // await updateSettings({ memberId: childId, tracking_enabled: value });
    } catch (e: any) {
      setTrackingEnabled(!value);
      setError(e?.message ?? 'Failed to update tracking setting.');
    }
  }

  async function handleRetentionChange(days: number) {
    setRetentionDays(days);
    try {
      // await updateSettings({ memberId: childId, history_retention_days: days });
    } catch (e: any) {
      setError(e?.message ?? 'Failed to update retention setting.');
    }
  }

  async function handleDeleteGeofence(id: string) {
    setDeletingId(id);
    try {
      // await deleteGeofence(id);
      setGeofences((prev) => prev.filter((g) => g.id !== id));
    } catch (e: any) {
      setError(e?.message ?? 'Failed to delete geofence.');
    } finally {
      setDeletingId(null);
    }
  }

  async function handleAddGeofence(
    name: string,
    type: GeofenceType,
    radiusMeters: number,
    alertsEnabled: boolean
  ) {
    setAddingGeofence(true);
    try {
      // const newFence = await createGeofence({
      //   group_id: groupId,
      //   name, lat: 0, lng: 0, radius_meters: radiusMeters, type, alerts_enabled: alertsEnabled,
      // });
      // setGeofences((prev) => [...prev, newFence]);
      setView('list');
    } catch (e: any) {
      setError(e?.message ?? 'Failed to add geofence.');
    } finally {
      setAddingGeofence(false);
    }
  }

  async function handleKillSwitch() {
    setTrackingEnabled(false);
    try {
      // await updateSettings({ memberId: childId, tracking_enabled: false });
    } catch (e: any) {
      setTrackingEnabled(true);
      setError(e?.message ?? 'Failed to disable tracking.');
    }
  }

  if (view === 'add') {
    return React.createElement(
      ScrollView,
      {
        style: styles.container,
        contentContainerStyle: styles.content,
        accessibilityLabel: 'Add Geofence',
      },
      React.createElement(
        Text,
        { style: styles.heading, accessibilityRole: 'header' },
        'Add Safe Zone'
      ),
      React.createElement(AddGeofenceForm, {
        onSubmit: handleAddGeofence,
        onCancel: () => setView('list'),
        loading: addingGeofence,
      })
    );
  }

  return React.createElement(
    ScrollView,
    {
      style: styles.container,
      contentContainerStyle: styles.content,
      accessibilityLabel: 'Location Settings',
    },
    React.createElement(
      Text,
      { style: styles.heading, accessibilityRole: 'header' },
      'Location Settings'
    ),

    // Error banner
    error
      ? React.createElement(
          Text,
          { style: styles.errorText, accessibilityRole: 'alert' },
          error
        )
      : null,

    // Tracking toggle card
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Location tracking toggle' },
      React.createElement(
        View,
        { style: styles.switchRow },
        React.createElement(
          View,
          { style: styles.switchInfo },
          React.createElement(Text, { style: styles.sectionTitle }, 'Location Tracking'),
          React.createElement(
            Text,
            { style: styles.infoText },
            "Track your child's location throughout the day"
          )
        ),
        React.createElement(Switch, {
          value: trackingEnabled,
          onValueChange: handleToggleTracking,
          trackColor: { true: colors.primary[500], false: colors.neutral[200] },
          thumbColor: '#FFFFFF',
          accessibilityLabel: 'Toggle location tracking',
        })
      )
    ),

    // History retention card
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'History retention settings' },
      React.createElement(Text, { style: styles.sectionTitle }, 'History Retention'),
      React.createElement(
        Text,
        { style: styles.infoText },
        'How long to keep location history'
      ),
      React.createElement(
        View,
        { style: styles.retentionRow },
        ...RETENTION_OPTIONS.map((opt) =>
          React.createElement(
            TouchableOpacity,
            {
              key: opt.value,
              style: [
                styles.retentionChip,
                retentionDays === opt.value ? styles.retentionChipActive : null,
              ],
              onPress: () => handleRetentionChange(opt.value),
              accessibilityRole: 'radio',
              accessibilityState: { selected: retentionDays === opt.value },
              accessibilityLabel: opt.label,
            },
            React.createElement(
              Text,
              {
                style: [
                  styles.retentionText,
                  retentionDays === opt.value ? styles.retentionTextActive : null,
                ],
              },
              opt.label
            )
          )
        )
      )
    ),

    // Geofences card
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Geofence management' },
      React.createElement(
        View,
        { style: styles.cardHeader },
        React.createElement(
          View,
          null,
          React.createElement(Text, { style: styles.sectionTitle }, 'Safe Zones'),
          React.createElement(
            Text,
            { style: styles.infoText },
            'Get alerts when your child arrives or leaves'
          )
        ),
        React.createElement(Button, {
          title: '+ Add',
          onPress: () => setView('add'),
          variant: 'outline',
          style: styles.addBtn,
          accessibilityLabel: 'Add safe zone',
        })
      ),
      geofences.length === 0
        ? React.createElement(
            Text,
            { style: styles.emptyText },
            'No safe zones configured. Add Home or School to get arrival alerts.'
          )
        : geofences.map((gf) =>
            React.createElement(GeofenceSettingsItem, {
              key: gf.id,
              geofence: gf,
              onDelete: handleDeleteGeofence,
              deleting: deletingId === gf.id,
            })
          )
    ),

    // Emergency kill switch
    React.createElement(
      Card,
      {
        style: [styles.card, styles.killSwitchCard],
        accessibilityLabel: 'Emergency disable all tracking',
      },
      React.createElement(Text, { style: styles.killSwitchTitle }, 'Emergency Stop'),
      React.createElement(
        Text,
        { style: styles.killSwitchInfo },
        'Immediately disable all location tracking. Your child will no longer be tracked until you re-enable it above.'
      ),
      React.createElement(
        TouchableOpacity,
        {
          style: styles.killSwitchBtn,
          onPress: handleKillSwitch,
          accessibilityLabel: 'Disable all location tracking immediately',
          accessibilityRole: 'button',
        },
        React.createElement(
          Text,
          { style: styles.killSwitchBtnText },
          'Disable All Tracking'
        )
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
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: spacing.sm,
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    minHeight: 48,
    gap: spacing.md,
  },
  switchInfo: {
    flex: 1,
    gap: 2,
  },
  sectionTitle: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  infoText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
    lineHeight: 18,
  },
  retentionRow: {
    flexDirection: 'row',
    gap: spacing.xs,
    marginTop: spacing.sm,
    flexWrap: 'wrap',
  },
  retentionChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 16,
    backgroundColor: colors.neutral[100],
    minHeight: 36,
    justifyContent: 'center',
  },
  retentionChipActive: {
    backgroundColor: colors.primary[600],
  },
  retentionText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
    fontWeight: '500',
  },
  retentionTextActive: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  addBtn: {
    paddingHorizontal: spacing.sm,
  },
  emptyText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
    textAlign: 'center',
    paddingVertical: spacing.sm,
    lineHeight: 20,
  },
  killSwitchCard: {
    borderWidth: 1,
    borderColor: colors.semantic.error + '40',
    backgroundColor: '#FEF2F2',
  },
  killSwitchTitle: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.semantic.error,
    fontFamily: typography.fontFamily,
    marginBottom: spacing.xs,
  },
  killSwitchInfo: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[600],
    fontFamily: typography.fontFamily,
    lineHeight: 20,
    marginBottom: spacing.md,
  },
  killSwitchBtn: {
    backgroundColor: colors.semantic.error,
    borderRadius: 8,
    paddingVertical: spacing.sm,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  killSwitchBtnText: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: '#FFFFFF',
    fontFamily: typography.fontFamily,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
    marginBottom: spacing.sm,
  },
});
