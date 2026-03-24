/**
 * Drawing Screen (P3-F1c)
 *
 * Child-facing drawing canvas screen. Uses a placeholder view until
 * react-native-skia is integrated. The CreativeToolbar is shown below
 * the canvas area.
 *
 * API: POST /api/v1/creative/drawings  (save drawing)
 * API: POST /api/v1/social/posts       (post to feed)
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { CreativeToolbar } from '@bhapi/ui';
import type { BrushSize } from '@bhapi/ui';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SaveState = 'idle' | 'saving' | 'saved' | 'error';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const DEFAULT_BRUSH_COLOR = '#1F2937';
export const DEFAULT_BRUSH_SIZE: BrushSize = 'medium';

// ---------------------------------------------------------------------------
// Canvas placeholder (exported for testing)
// ---------------------------------------------------------------------------

export interface CanvasPlaceholderProps {
  width?: number;
  height?: number;
}

export function CanvasPlaceholder({ width, height = 320 }: CanvasPlaceholderProps) {
  return React.createElement(
    View,
    {
      style: [
        canvasStyles.container,
        width ? { width } : null,
        { height },
      ],
      testID: 'drawing-canvas-placeholder',
      accessibilityLabel: 'Drawing canvas',
    },
    React.createElement(
      Text,
      { style: canvasStyles.icon },
      '\uD83C\uDFA8'
    ),
    React.createElement(
      Text,
      { style: canvasStyles.label },
      'Drawing canvas'
    ),
    React.createElement(
      Text,
      { style: canvasStyles.sublabel },
      'Requires react-native-skia'
    )
  );
}

const canvasStyles = StyleSheet.create({
  container: {
    borderWidth: 2,
    borderColor: colors.neutral[300],
    borderStyle: 'dashed',
    borderRadius: 12,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  icon: {
    fontSize: 48,
    marginBottom: spacing.sm,
  },
  label: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  sublabel: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
    marginTop: 4,
  },
});

// ---------------------------------------------------------------------------
// Main Screen
// ---------------------------------------------------------------------------

export default function DrawingScreen() {
  const [brushColor, setBrushColor] = useState(DEFAULT_BRUSH_COLOR);
  const [brushSize, setBrushSize] = useState<BrushSize>(DEFAULT_BRUSH_SIZE);
  const [isErasing, setIsErasing] = useState(false);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  function handleColorChange(color: string) {
    setBrushColor(color);
    setIsErasing(false);
  }

  function handleErase() {
    setIsErasing(true);
  }

  function handleUndo() {
    // Will interact with Skia canvas ref in Phase 2
    if (canUndo) {
      setCanRedo(true);
    }
  }

  function handleRedo() {
    // Will interact with Skia canvas ref in Phase 2
    if (canRedo) {
      setCanUndo(true);
    }
  }

  async function handleSave() {
    setSaveState('saving');
    setErrorMessage('');

    try {
      // API: POST /api/v1/creative/drawings
      // const drawing = await apiClient.post('/api/v1/creative/drawings', {
      //   image_data: canvasRef.current?.toBase64(),
      // });
      setSaveState('saved');
    } catch (e: any) {
      setErrorMessage(e?.message ?? 'Could not save drawing. Please try again.');
      setSaveState('error');
    }
  }

  async function handlePostToFeed() {
    // API: POST /api/v1/social/posts with drawing reference
    // Placeholder — will be wired in Phase 2
  }

  return React.createElement(
    View,
    { style: styles.container },
    // Header
    React.createElement(
      View,
      { style: styles.header },
      React.createElement(
        Text,
        { style: styles.title },
        '\u270F\uFE0F Drawing'
      )
    ),
    // Scrollable canvas area
    React.createElement(
      ScrollView,
      {
        style: styles.scrollArea,
        contentContainerStyle: styles.scrollContent,
        scrollEnabled: false,
      },
      // Mode indicator
      isErasing
        ? React.createElement(
            View,
            { style: styles.erasingBanner },
            React.createElement(
              Text,
              { style: styles.erasingText },
              '\u2421 Erasing mode — tap a color to draw again'
            )
          )
        : null,
      // Canvas placeholder
      React.createElement(CanvasPlaceholder, { height: 320 }),
      // Error message
      errorMessage
        ? React.createElement(
            Text,
            { style: styles.errorText, accessibilityRole: 'alert' },
            errorMessage
          )
        : null,
      // Action buttons
      React.createElement(
        View,
        { style: styles.actionRow },
        React.createElement(
          TouchableOpacity,
          {
            style: styles.saveButton,
            onPress: handleSave,
            disabled: saveState === 'saving',
            accessibilityLabel: 'Save drawing',
            accessibilityRole: 'button',
            testID: 'save-button',
          },
          saveState === 'saving'
            ? React.createElement(ActivityIndicator, { size: 'small', color: '#FFFFFF' })
            : React.createElement(
                Text,
                { style: styles.saveButtonText },
                saveState === 'saved' ? '\u2713 Saved!' : 'Save'
              )
        ),
        React.createElement(
          TouchableOpacity,
          {
            style: styles.postButton,
            onPress: handlePostToFeed,
            accessibilityLabel: 'Post to Feed',
            accessibilityRole: 'button',
            testID: 'post-to-feed-button',
          },
          React.createElement(
            Text,
            { style: styles.postButtonText },
            'Post to Feed'
          )
        )
      )
    ),
    // Toolbar at the bottom
    React.createElement(CreativeToolbar, {
      selectedColor: isErasing ? '#FFFFFF' : brushColor,
      selectedSize: brushSize,
      onColorChange: handleColorChange,
      onSizeChange: setBrushSize,
      onErase: handleErase,
      onUndo: handleUndo,
      onRedo: handleRedo,
      canUndo,
      canRedo,
    })
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  header: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
  },
  title: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  scrollArea: {
    flex: 1,
  },
  scrollContent: {
    padding: spacing.md,
    paddingBottom: spacing.xl,
  },
  erasingBanner: {
    backgroundColor: '#FEF3C7',
    borderRadius: 8,
    padding: spacing.sm,
    marginBottom: spacing.sm,
  },
  erasingText: {
    fontSize: typography.sizes.sm,
    color: '#92400E',
    fontFamily: typography.fontFamily,
    textAlign: 'center',
  },
  actionRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  saveButton: {
    flex: 1,
    backgroundColor: colors.neutral[700],
    borderRadius: 12,
    paddingVertical: spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  saveButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  postButton: {
    flex: 2,
    backgroundColor: colors.primary[600],
    borderRadius: 12,
    paddingVertical: spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  postButtonText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
});
