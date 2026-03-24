/**
 * CreativeToolbar — Horizontal drawing toolbar for the Bhapi Social app.
 *
 * Provides:
 *   - Color picker: 8 preset colors as circular buttons
 *   - Size presets: thin / medium / thick
 *   - Tool buttons: eraser, undo, redo
 *
 * Designed for the drawing canvas screen (social app, child-facing).
 */
import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ViewStyle,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type BrushSize = 'thin' | 'medium' | 'thick';

export interface CreativeToolbarProps {
  /** Currently selected color (hex string). */
  selectedColor?: string;
  /** Currently selected brush size. */
  selectedSize?: BrushSize;
  /** Called when the user selects a color. */
  onColorChange: (color: string) => void;
  /** Called when the user selects a size. */
  onSizeChange: (size: BrushSize) => void;
  /** Called when the eraser tool is tapped. */
  onErase: () => void;
  /** Called when the undo button is tapped. */
  onUndo: () => void;
  /** Called when the redo button is tapped. */
  onRedo: () => void;
  /** Whether undo is available. */
  canUndo?: boolean;
  /** Whether redo is available. */
  canRedo?: boolean;
  /** Custom style overrides for the container. */
  style?: ViewStyle;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const PRESET_COLORS = [
  { label: 'Red', value: '#EF4444' },
  { label: 'Orange', value: '#F97316' },
  { label: 'Yellow', value: '#EAB308' },
  { label: 'Green', value: '#22C55E' },
  { label: 'Blue', value: '#3B82F6' },
  { label: 'Purple', value: '#A855F7' },
  { label: 'Pink', value: '#EC4899' },
  { label: 'Black', value: '#1F2937' },
];

export const SIZE_PRESETS: Array<{ label: string; value: BrushSize; diameter: number }> = [
  { label: 'Thin', value: 'thin', diameter: 4 },
  { label: 'Medium', value: 'medium', diameter: 8 },
  { label: 'Thick', value: 'thick', diameter: 14 },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CreativeToolbar({
  selectedColor = '#1F2937',
  selectedSize = 'medium',
  onColorChange,
  onSizeChange,
  onErase,
  onUndo,
  onRedo,
  canUndo = false,
  canRedo = false,
  style,
}: CreativeToolbarProps) {
  return React.createElement(
    View,
    {
      style: [styles.container, style],
      accessibilityLabel: 'Drawing toolbar',
      accessibilityRole: 'toolbar',
    },
    // Color picker row
    React.createElement(
      View,
      { style: styles.section },
      ...PRESET_COLORS.map((c) =>
        React.createElement(
          TouchableOpacity,
          {
            key: c.value,
            style: [
              styles.colorCircle,
              { backgroundColor: c.value },
              selectedColor === c.value ? styles.colorCircleSelected : null,
            ],
            onPress: () => onColorChange(c.value),
            accessibilityLabel: `${c.label} color`,
            accessibilityRole: 'button',
            accessibilityState: { selected: selectedColor === c.value },
            testID: `color-${c.label.toLowerCase()}`,
          }
        )
      )
    ),
    // Size presets + tools row
    React.createElement(
      View,
      { style: [styles.section, styles.toolsRow] },
      // Size presets
      ...SIZE_PRESETS.map((s) =>
        React.createElement(
          TouchableOpacity,
          {
            key: s.value,
            style: [
              styles.sizeButton,
              selectedSize === s.value ? styles.sizeButtonSelected : null,
            ],
            onPress: () => onSizeChange(s.value),
            accessibilityLabel: `${s.label} brush`,
            accessibilityRole: 'button',
            accessibilityState: { selected: selectedSize === s.value },
            testID: `size-${s.value}`,
          },
          React.createElement(View, {
            style: [
              styles.sizeDot,
              {
                width: s.diameter,
                height: s.diameter,
                borderRadius: s.diameter / 2,
                backgroundColor: selectedColor,
              },
            ],
          })
        )
      ),
      // Divider
      React.createElement(View, { style: styles.divider }),
      // Eraser
      React.createElement(
        TouchableOpacity,
        {
          style: styles.toolButton,
          onPress: onErase,
          accessibilityLabel: 'Eraser tool',
          accessibilityRole: 'button',
          testID: 'tool-eraser',
        },
        React.createElement(Text, { style: styles.toolIcon }, '\u2421')
      ),
      // Undo
      React.createElement(
        TouchableOpacity,
        {
          style: [styles.toolButton, !canUndo ? styles.toolButtonDisabled : null],
          onPress: onUndo,
          disabled: !canUndo,
          accessibilityLabel: 'Undo',
          accessibilityRole: 'button',
          accessibilityState: { disabled: !canUndo },
          testID: 'tool-undo',
        },
        React.createElement(Text, { style: [styles.toolIcon, !canUndo ? styles.toolIconDisabled : null] }, '\u21A9')
      ),
      // Redo
      React.createElement(
        TouchableOpacity,
        {
          style: [styles.toolButton, !canRedo ? styles.toolButtonDisabled : null],
          onPress: onRedo,
          disabled: !canRedo,
          accessibilityLabel: 'Redo',
          accessibilityRole: 'button',
          accessibilityState: { disabled: !canRedo },
          testID: 'tool-redo',
        },
        React.createElement(Text, { style: [styles.toolIcon, !canRedo ? styles.toolIconDisabled : null] }, '\u21AA')
      )
    )
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

export const creativeToolbarStyles = {
  height: 88,
  borderTopWidth: 1,
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: colors.neutral[200],
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  section: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  toolsRow: {
    marginBottom: 0,
  },
  colorCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    marginRight: spacing.xs,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  colorCircleSelected: {
    borderColor: colors.neutral[900],
    transform: [{ scale: 1.15 }] as any,
  },
  sizeButton: {
    width: 36,
    height: 36,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.xs,
    backgroundColor: colors.neutral[100],
  },
  sizeButtonSelected: {
    backgroundColor: colors.primary[100],
    borderWidth: 1,
    borderColor: colors.primary[400],
  },
  sizeDot: {
    // dynamic styles applied inline
  },
  divider: {
    width: 1,
    height: 28,
    backgroundColor: colors.neutral[200],
    marginHorizontal: spacing.xs,
  },
  toolButton: {
    width: 36,
    height: 36,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: spacing.xs,
    backgroundColor: colors.neutral[100],
  },
  toolButtonDisabled: {
    opacity: 0.4,
  },
  toolIcon: {
    fontSize: 18,
    color: colors.neutral[700],
  },
  toolIconDisabled: {
    color: colors.neutral[400],
  },
});
