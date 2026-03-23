/**
 * Screen Time Settings Screen
 *
 * Rules management: list, create, edit, delete.
 * Schedule management per rule (bedtime blocks, etc.).
 * Category presets: social, games, education, all.
 * Enforcement mode selector.
 *
 * API: GET /api/v1/screen-time/rules?member_id=<id>&group_id=<id>
 * API: POST/PUT/DELETE /api/v1/screen-time/rules/<id>
 * API: POST/DELETE /api/v1/screen-time/schedules
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Switch,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Badge, Button, Card } from '@bhapi/ui';
import type {
  ScreenTimeRule,
  AppCategory,
  EnforcementAction,
} from '@bhapi/types';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const CATEGORY_PRESETS: { value: AppCategory; label: string; emoji: string }[] = [
  { value: 'social', label: 'Social Media', emoji: '💬' },
  { value: 'games', label: 'Games', emoji: '🎮' },
  { value: 'education', label: 'Education', emoji: '📚' },
  { value: 'entertainment', label: 'Entertainment', emoji: '🎬' },
  { value: 'productivity', label: 'Productivity', emoji: '📝' },
  { value: 'all', label: 'All Apps', emoji: '📱' },
];

export const ENFORCEMENT_OPTIONS: { value: EnforcementAction; label: string; description: string }[] = [
  {
    value: 'hard_block',
    label: 'Hard Block',
    description: 'App is blocked when limit is reached',
  },
  {
    value: 'warning_then_block',
    label: 'Warn then Block',
    description: 'Warning at 80%, blocked at 100%',
  },
  {
    value: 'warning_only',
    label: 'Warning Only',
    description: 'Notification only, no blocking',
  },
];

export const LIMIT_PRESETS = [30, 60, 90, 120, 180, 240];

// ---------------------------------------------------------------------------
// Rule item (exported for testing)
// ---------------------------------------------------------------------------

interface RuleItemProps {
  rule: ScreenTimeRule;
  onToggle: (ruleId: string, enabled: boolean) => void;
  onDelete: (ruleId: string) => void;
  deleting?: boolean;
}

export function RuleItem({ rule, onToggle, onDelete, deleting }: RuleItemProps) {
  const categoryLabel =
    CATEGORY_PRESETS.find((c) => c.value === rule.app_category)?.label ?? rule.app_category;

  return React.createElement(
    View,
    { style: ruleStyles.container, accessibilityLabel: `Rule: ${categoryLabel}` },
    React.createElement(
      View,
      { style: ruleStyles.left },
      React.createElement(
        Text,
        { style: ruleStyles.category },
        categoryLabel
      ),
      React.createElement(
        Text,
        { style: ruleStyles.limit },
        `${rule.daily_limit_minutes} min/day`
      ),
      rule.age_tier_enforcement
        ? React.createElement(Badge, { text: 'Age-enforced', variant: 'info' })
        : null
    ),
    React.createElement(
      View,
      { style: ruleStyles.right },
      React.createElement(Switch, {
        value: rule.enabled,
        onValueChange: (val: boolean) => onToggle(rule.id, val),
        trackColor: { true: colors.primary[500], false: colors.neutral[200] },
        thumbColor: '#FFFFFF',
        accessibilityLabel: `Toggle ${categoryLabel} rule`,
      }),
      React.createElement(
        TouchableOpacity,
        {
          onPress: () => onDelete(rule.id),
          disabled: deleting,
          style: ruleStyles.deleteBtn,
          accessibilityLabel: `Delete ${categoryLabel} rule`,
          accessibilityRole: 'button',
        },
        React.createElement(
          Text,
          { style: ruleStyles.deleteText },
          deleting ? '...' : 'Delete'
        )
      )
    )
  );
}

const ruleStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
    minHeight: 56,
  },
  left: {
    flex: 1,
    gap: 2,
  },
  category: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  limit: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  right: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
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
// Create rule form (exported for testing)
// ---------------------------------------------------------------------------

interface CreateRuleFormProps {
  onSubmit: (category: AppCategory, limitMinutes: number, enforcement: EnforcementAction) => void;
  onCancel: () => void;
  loading?: boolean;
}

export function CreateRuleForm({ onSubmit, onCancel, loading }: CreateRuleFormProps) {
  const [selectedCategory, setSelectedCategory] = useState<AppCategory>('social');
  const [limitMinutes, setLimitMinutes] = useState(60);
  const [enforcement, setEnforcement] = useState<EnforcementAction>('warning_then_block');

  return React.createElement(
    View,
    { style: formStyles.container, accessibilityLabel: 'Create screen time rule' },

    // Category selector
    React.createElement(Text, { style: formStyles.label }, 'Category'),
    React.createElement(
      View,
      { style: formStyles.presetRow },
      ...CATEGORY_PRESETS.map((cat) =>
        React.createElement(
          TouchableOpacity,
          {
            key: cat.value,
            style: [
              formStyles.presetChip,
              selectedCategory === cat.value ? formStyles.presetChipActive : null,
            ],
            onPress: () => setSelectedCategory(cat.value),
            accessibilityRole: 'radio',
            accessibilityState: { selected: selectedCategory === cat.value },
            accessibilityLabel: cat.label,
          },
          React.createElement(
            Text,
            {
              style: [
                formStyles.presetText,
                selectedCategory === cat.value ? formStyles.presetTextActive : null,
              ],
            },
            cat.label
          )
        )
      )
    ),

    // Daily limit
    React.createElement(Text, { style: formStyles.label }, 'Daily Limit'),
    React.createElement(
      View,
      { style: formStyles.presetRow },
      ...LIMIT_PRESETS.map((min) =>
        React.createElement(
          TouchableOpacity,
          {
            key: min,
            style: [
              formStyles.limitChip,
              limitMinutes === min ? formStyles.presetChipActive : null,
            ],
            onPress: () => setLimitMinutes(min),
            accessibilityRole: 'radio',
            accessibilityState: { selected: limitMinutes === min },
            accessibilityLabel: `${min} minutes`,
          },
          React.createElement(
            Text,
            {
              style: [
                formStyles.limitText,
                limitMinutes === min ? formStyles.presetTextActive : null,
              ],
            },
            min >= 60 ? `${min / 60}h` : `${min}m`
          )
        )
      )
    ),

    // Enforcement mode
    React.createElement(Text, { style: formStyles.label }, 'Enforcement'),
    React.createElement(
      View,
      { style: formStyles.enforcementList },
      ...ENFORCEMENT_OPTIONS.map((opt) =>
        React.createElement(
          TouchableOpacity,
          {
            key: opt.value,
            style: [
              formStyles.enforcementOption,
              enforcement === opt.value ? formStyles.enforcementOptionActive : null,
            ],
            onPress: () => setEnforcement(opt.value),
            accessibilityRole: 'radio',
            accessibilityState: { selected: enforcement === opt.value },
            accessibilityLabel: `${opt.label}: ${opt.description}`,
          },
          React.createElement(Text, { style: formStyles.enforcementLabel }, opt.label),
          React.createElement(Text, { style: formStyles.enforcementDesc }, opt.description)
        )
      )
    ),

    // Actions
    React.createElement(
      View,
      { style: formStyles.actions },
      React.createElement(
        TouchableOpacity,
        {
          style: formStyles.cancelBtn,
          onPress: onCancel,
          accessibilityLabel: 'Cancel',
        },
        React.createElement(Text, { style: formStyles.cancelText }, 'Cancel')
      ),
      React.createElement(Button, {
        title: loading ? 'Saving...' : 'Create Rule',
        onPress: () => onSubmit(selectedCategory, limitMinutes, enforcement),
        variant: 'primary',
        style: formStyles.submitBtn,
        accessibilityLabel: 'Create screen time rule',
      })
    )
  );
}

const formStyles = StyleSheet.create({
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
  presetRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
  },
  presetChip: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: 16,
    backgroundColor: colors.neutral[100],
    minHeight: 36,
    justifyContent: 'center',
  },
  presetChipActive: {
    backgroundColor: colors.primary[600],
  },
  presetText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
  },
  presetTextActive: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  limitChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 8,
    backgroundColor: colors.neutral[100],
    minHeight: 36,
    justifyContent: 'center',
    alignItems: 'center',
  },
  limitText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
    fontWeight: '500',
  },
  enforcementList: {
    gap: spacing.xs,
  },
  enforcementOption: {
    padding: spacing.sm,
    borderRadius: 8,
    backgroundColor: colors.neutral[50],
    borderWidth: 1,
    borderColor: colors.neutral[200],
  },
  enforcementOptionActive: {
    borderColor: colors.primary[500],
    backgroundColor: colors.primary[50],
  },
  enforcementLabel: {
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  enforcementDesc: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
    marginTop: 2,
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
// Main Settings Screen
// ---------------------------------------------------------------------------

type SettingsView = 'list' | 'create';

export default function ScreenTimeSettings() {
  const [rules, setRules] = useState<ScreenTimeRule[]>([]);
  const [view, setView] = useState<SettingsView>('list');
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState('');

  // In production, replace with:
  // const { data: rulesData } = useScreenTimeRules(childId, groupId);
  // const { mutateAsync: createRule } = useCreateRule();
  // const { mutateAsync: updateRule } = useUpdateRule();
  // const { mutateAsync: deleteRule } = useDeleteRule();

  async function handleToggleRule(ruleId: string, enabled: boolean) {
    setRules((prev) =>
      prev.map((r) => (r.id === ruleId ? { ...r, enabled } : r))
    );
    try {
      // await updateRule({ ruleId, enabled });
    } catch (e: any) {
      // Revert on error
      setRules((prev) =>
        prev.map((r) => (r.id === ruleId ? { ...r, enabled: !enabled } : r))
      );
      setError(e?.message ?? 'Failed to update rule.');
    }
  }

  async function handleDeleteRule(ruleId: string) {
    setDeletingId(ruleId);
    try {
      // await deleteRule(ruleId);
      setRules((prev) => prev.filter((r) => r.id !== ruleId));
    } catch (e: any) {
      setError(e?.message ?? 'Failed to delete rule.');
    } finally {
      setDeletingId(null);
    }
  }

  async function handleCreateRule(
    category: AppCategory,
    limitMinutes: number,
    enforcement: EnforcementAction
  ) {
    setLoading(true);
    try {
      // const newRule = await createRule({
      //   member_id: childId,
      //   group_id: groupId,
      //   app_category: category,
      //   daily_limit_minutes: limitMinutes,
      //   age_tier_enforcement: false,
      //   enabled: true,
      // });
      // setRules((prev) => [...prev, newRule]);
      setView('list');
    } catch (e: any) {
      setError(e?.message ?? 'Failed to create rule.');
    } finally {
      setLoading(false);
    }
  }

  if (view === 'create') {
    return React.createElement(
      ScrollView,
      { style: styles.container, contentContainerStyle: styles.content, accessibilityLabel: 'Create Screen Time Rule' },
      React.createElement(
        Text,
        { style: styles.heading, accessibilityRole: 'header' },
        'New Rule'
      ),
      React.createElement(CreateRuleForm, {
        onSubmit: handleCreateRule,
        onCancel: () => setView('list'),
        loading,
      })
    );
  }

  return React.createElement(
    ScrollView,
    {
      style: styles.container,
      contentContainerStyle: styles.content,
      accessibilityLabel: 'Screen Time Settings',
    },
    React.createElement(
      Text,
      { style: styles.heading, accessibilityRole: 'header' },
      'Screen Time Settings'
    ),

    // Error banner
    error
      ? React.createElement(
          Text,
          { style: styles.errorText, accessibilityRole: 'alert' },
          error
        )
      : null,

    // Rules card
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Screen time rules' },
      React.createElement(
        View,
        { style: styles.cardHeader },
        React.createElement(Text, { style: styles.sectionTitle }, 'Rules'),
        React.createElement(Button, {
          title: '+ Add Rule',
          onPress: () => setView('create'),
          variant: 'outline',
          style: styles.addButton,
          accessibilityLabel: 'Add screen time rule',
        })
      ),
      rules.length === 0
        ? React.createElement(
            Text,
            { style: styles.emptyText },
            'No rules yet. Add a rule to set daily limits.'
          )
        : rules.map((rule) =>
            React.createElement(RuleItem, {
              key: rule.id,
              rule,
              onToggle: handleToggleRule,
              onDelete: handleDeleteRule,
              deleting: deletingId === rule.id,
            })
          )
    ),

    // Schedules info card
    React.createElement(
      Card,
      { style: styles.card, accessibilityLabel: 'Blocked time schedules' },
      React.createElement(Text, { style: styles.sectionTitle }, 'Blocked Periods'),
      React.createElement(
        Text,
        { style: styles.infoText },
        'Set specific time blocks (e.g. bedtime) when apps are always blocked, regardless of daily limits.'
      ),
      rules.length === 0
        ? React.createElement(
            Text,
            { style: styles.emptyText },
            'Create a rule first to add schedules.'
          )
        : React.createElement(
            Text,
            { style: styles.emptyText },
            'Manage schedules per rule from the rule detail view.'
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
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  sectionTitle: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  addButton: {
    paddingHorizontal: spacing.sm,
  },
  emptyText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[400],
    fontFamily: typography.fontFamily,
    textAlign: 'center',
    paddingVertical: spacing.sm,
  },
  infoText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
    lineHeight: 20,
    marginBottom: spacing.sm,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
    marginBottom: spacing.sm,
  },
});
