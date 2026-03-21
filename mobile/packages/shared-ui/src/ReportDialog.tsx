/**
 * ReportDialog — Modal for reporting posts, users, or messages.
 *
 * Displays age-appropriate reason labels with radio-button selection
 * and an optional description text field.
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  TextInput,
  StyleSheet,
  ViewStyle,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

export type ReportTargetType = 'post' | 'comment' | 'message' | 'user';

export type ReportReasonValue =
  | 'inappropriate'
  | 'bullying'
  | 'spam'
  | 'impersonation'
  | 'self_harm'
  | 'adult_content'
  | 'other';

export interface ReportReasonOption {
  value: ReportReasonValue;
  label: string;
}

/**
 * Default reasons with age-appropriate labels suitable for children 5-15.
 */
export const DEFAULT_REPORT_REASONS: ReportReasonOption[] = [
  { value: 'inappropriate', label: 'Something inappropriate' },
  { value: 'bullying', label: 'Bullying or mean behavior' },
  { value: 'spam', label: 'Spam or unwanted content' },
  { value: 'impersonation', label: 'Pretending to be someone else' },
  { value: 'self_harm', label: 'Someone might be hurting themselves' },
  { value: 'adult_content', label: "Grown-up content that shouldn't be here" },
  { value: 'other', label: 'Something else' },
];

export interface ReportDialogProps {
  visible: boolean;
  targetType: ReportTargetType;
  targetId: string;
  reasons?: ReportReasonOption[];
  onSubmit: (data: {
    targetType: ReportTargetType;
    targetId: string;
    reason: ReportReasonValue;
    description?: string;
  }) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
  style?: ViewStyle;
  accessibilityLabel?: string;
}

export function ReportDialog({
  visible,
  targetType,
  targetId,
  reasons = DEFAULT_REPORT_REASONS,
  onSubmit,
  onCancel,
  isSubmitting = false,
  style,
  accessibilityLabel,
}: ReportDialogProps) {
  const [selectedReason, setSelectedReason] =
    useState<ReportReasonValue | null>(null);
  const [description, setDescription] = useState('');

  if (!visible) {
    return null;
  }

  const targetLabel =
    targetType === 'user'
      ? 'person'
      : targetType === 'message'
        ? 'message'
        : targetType === 'comment'
          ? 'comment'
          : 'post';

  const handleSubmit = () => {
    if (!selectedReason) return;
    onSubmit({
      targetType,
      targetId,
      reason: selectedReason,
      description: description.trim() || undefined,
    });
  };

  return React.createElement(
    View,
    {
      style: [styles.overlay, style],
      accessibilityLabel: accessibilityLabel ?? `Report this ${targetLabel}`,
    },
    React.createElement(
      View,
      { style: styles.dialog },
      // Title
      React.createElement(
        Text,
        { style: styles.title },
        `Report this ${targetLabel}`
      ),
      // Subtitle
      React.createElement(
        Text,
        { style: styles.subtitle },
        'Why are you reporting this? Your report is confidential.'
      ),
      // Reason options (radio buttons)
      ...reasons.map((reason) =>
        React.createElement(
          TouchableOpacity,
          {
            key: reason.value,
            style: [
              styles.reasonRow,
              selectedReason === reason.value ? styles.reasonRowSelected : null,
            ],
            onPress: () => setSelectedReason(reason.value),
            accessibilityLabel: reason.label,
            accessibilityRole: 'radio',
          },
          React.createElement(
            View,
            {
              style: [
                styles.radio,
                selectedReason === reason.value ? styles.radioSelected : null,
              ],
            },
            selectedReason === reason.value
              ? React.createElement(View, { style: styles.radioDot })
              : null
          ),
          React.createElement(
            Text,
            { style: styles.reasonLabel },
            reason.label
          )
        )
      ),
      // Description text input
      React.createElement(TextInput, {
        style: styles.descriptionInput,
        placeholder: 'Tell us more (optional)',
        value: description,
        onChangeText: setDescription,
        multiline: true,
        maxLength: 2000,
        accessibilityLabel: 'Additional details',
      }),
      // Action buttons
      React.createElement(
        View,
        { style: styles.buttonRow },
        React.createElement(
          TouchableOpacity,
          {
            style: styles.cancelButton,
            onPress: onCancel,
            accessibilityLabel: 'Cancel report',
          },
          React.createElement(Text, { style: styles.cancelText }, 'Cancel')
        ),
        React.createElement(
          TouchableOpacity,
          {
            style: [
              styles.submitButton,
              (!selectedReason || isSubmitting) ? styles.submitButtonDisabled : null,
            ],
            onPress: handleSubmit,
            disabled: !selectedReason || isSubmitting,
            accessibilityLabel: 'Submit report',
          },
          React.createElement(
            Text,
            {
              style: [
                styles.submitText,
                (!selectedReason || isSubmitting) ? styles.submitTextDisabled : null,
              ],
            },
            isSubmitting ? 'Sending...' : 'Report'
          )
        )
      )
    )
  );
}

export const reportDialogStyles = {
  overlayBg: 'rgba(0, 0, 0, 0.5)',
  dialogBg: '#FFFFFF',
  borderRadius: 16,
};

const styles = StyleSheet.create({
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  dialog: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: spacing.lg,
    width: '100%',
    maxWidth: 400,
    maxHeight: '80%',
  },
  title: {
    fontSize: typography.sizes.lg,
    fontWeight: '700',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
    marginBottom: spacing.xs,
  },
  subtitle: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
    marginBottom: spacing.md,
  },
  reasonRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
    borderRadius: 8,
    marginBottom: spacing.xs,
    minHeight: 44,
  },
  reasonRowSelected: {
    backgroundColor: colors.primary[50] ?? '#FFF7ED',
  },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.neutral[300],
    marginRight: spacing.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioSelected: {
    borderColor: colors.primary[600] ?? '#FF6B35',
  },
  radioDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.primary[600] ?? '#FF6B35',
  },
  reasonLabel: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
    flex: 1,
  },
  descriptionInput: {
    borderWidth: 1,
    borderColor: colors.neutral[200],
    borderRadius: 8,
    padding: spacing.sm,
    marginTop: spacing.md,
    minHeight: 80,
    textAlignVertical: 'top',
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: spacing.sm,
    marginTop: spacing.lg,
  },
  cancelButton: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    borderRadius: 8,
    minHeight: 44,
    justifyContent: 'center',
  },
  cancelText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  submitButton: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    borderRadius: 8,
    backgroundColor: colors.semantic?.error ?? '#EF4444',
    minHeight: 44,
    justifyContent: 'center',
  },
  submitButtonDisabled: {
    backgroundColor: colors.neutral[200],
  },
  submitText: {
    fontSize: typography.sizes.base,
    color: '#FFFFFF',
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  submitTextDisabled: {
    color: colors.neutral[400],
  },
});
