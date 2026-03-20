/**
 * Dashboard Tab Layout
 *
 * Tab navigation with 4 tabs: Dashboard, Alerts, Children, Settings.
 * In Expo Router, this uses expo-router Tabs component.
 */
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

interface TabConfig {
  key: string;
  label: string;
  accessibilityLabel: string;
}

const TABS: TabConfig[] = [
  { key: 'index', label: 'Dashboard', accessibilityLabel: 'Dashboard tab' },
  { key: 'alerts', label: 'Alerts', accessibilityLabel: 'Alerts tab' },
  { key: 'children', label: 'Children', accessibilityLabel: 'Children tab' },
  { key: 'settings', label: 'Settings', accessibilityLabel: 'Settings tab' },
];

export default function DashboardLayout() {
  // In Expo Router, this would use <Tabs> with <Tabs.Screen> for each tab.
  // The active tab renders via <Slot />.
  return React.createElement(
    View,
    { style: styles.container, accessibilityLabel: 'Dashboard navigation' },
    // Content area — <Slot /> in Expo Router
    React.createElement(View, { style: styles.content }),
    // Tab bar
    React.createElement(
      View,
      { style: styles.tabBar, accessibilityRole: 'tablist' },
      ...TABS.map((tab) =>
        React.createElement(
          TouchableOpacity,
          {
            key: tab.key,
            style: styles.tab,
            accessibilityLabel: tab.accessibilityLabel,
            accessibilityRole: 'tab',
          },
          React.createElement(
            Text,
            { style: styles.tabLabel },
            tab.label
          )
        )
      )
    )
  );
}

// Exported for testing
export { TABS, type TabConfig };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  content: {
    flex: 1,
  },
  tabBar: {
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: colors.neutral[200],
    backgroundColor: '#FFFFFF',
    paddingBottom: 20, // Safe area bottom
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing.sm,
    minHeight: 44,
    justifyContent: 'center',
  },
  tabLabel: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
});
