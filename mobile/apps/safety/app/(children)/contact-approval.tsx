/**
 * Contact Approval Screen (P2-M5)
 *
 * Parent reviews pending contact requests from their children.
 * Shows requester profile info, approve/deny per-request, and batch actions.
 *
 * API: GET /api/v1/contacts/pending-with-profiles
 * API: PATCH /api/v1/contacts/:id/parent-approve { decision }
 * API: POST /api/v1/contacts/batch-approve { contact_ids, decision }
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Alert,
  RefreshControl,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Card, Badge, Avatar, Button } from '@bhapi/ui';

interface ContactApprovalItem {
  id: string;
  requester_id: string;
  target_id: string;
  status: string;
  parent_approval_status: string;
  created_at: string;
  requester_display_name: string | null;
  requester_age_tier: string | null;
  requester_avatar_url: string | null;
  target_display_name: string | null;
  target_age_tier: string | null;
  target_avatar_url: string | null;
}

interface PendingResponse {
  items: ContactApprovalItem[];
  total: number;
  page: number;
  page_size: number;
}

type ScreenState = 'loading' | 'loaded' | 'error';

export default function ContactApprovalScreen() {
  const [items, setItems] = useState<ContactApprovalItem[]>([]);
  const [state, setState] = useState<ScreenState>('loading');
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [processing, setProcessing] = useState<Set<string>>(new Set());
  const [batchProcessing, setBatchProcessing] = useState(false);

  useEffect(() => {
    loadPending();
  }, []);

  async function loadPending() {
    try {
      setState('loading');
      // API call: GET /api/v1/contacts/pending-with-profiles
      // const response = await apiClient.get<PendingResponse>('/api/v1/contacts/pending-with-profiles');
      // setItems(response.items);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Failed to load pending approvals.');
    }
  }

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      // const response = await apiClient.get<PendingResponse>('/api/v1/contacts/pending-with-profiles');
      // setItems(response.items);
      setState('loaded');
    } catch (e: any) {
      setError(e?.message ?? 'Failed to refresh.');
    } finally {
      setRefreshing(false);
    }
  }, []);

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function selectAll() {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((i) => i.id)));
    }
  }

  async function handleSingleDecision(contactId: string, decision: 'approve' | 'deny') {
    setProcessing((prev) => new Set(prev).add(contactId));
    try {
      // API call: PATCH /api/v1/contacts/:id/parent-approve
      // await apiClient.patch(`/api/v1/contacts/${contactId}/parent-approve`, { decision });
      setItems((prev) => prev.filter((item) => item.id !== contactId));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(contactId);
        return next;
      });
    } catch (e: any) {
      Alert.alert('Error', e?.message ?? `Failed to ${decision} request.`);
    } finally {
      setProcessing((prev) => {
        const next = new Set(prev);
        next.delete(contactId);
        return next;
      });
    }
  }

  async function handleBatchDecision(decision: 'approve' | 'deny') {
    if (selectedIds.size === 0) return;

    const label = decision === 'approve' ? 'approve' : 'deny';
    const count = selectedIds.size;

    Alert.alert(
      `${label.charAt(0).toUpperCase() + label.slice(1)} ${count} Request${count > 1 ? 's' : ''}?`,
      `Are you sure you want to ${label} ${count} contact request${count > 1 ? 's' : ''}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: label.charAt(0).toUpperCase() + label.slice(1),
          style: decision === 'deny' ? 'destructive' : 'default',
          onPress: async () => {
            setBatchProcessing(true);
            try {
              // API call: POST /api/v1/contacts/batch-approve
              // await apiClient.post('/api/v1/contacts/batch-approve', {
              //   contact_ids: Array.from(selectedIds),
              //   decision,
              // });
              setItems((prev) => prev.filter((item) => !selectedIds.has(item.id)));
              setSelectedIds(new Set());
            } catch (e: any) {
              Alert.alert('Error', e?.message ?? `Failed to ${label} requests.`);
            } finally {
              setBatchProcessing(false);
            }
          },
        },
      ]
    );
  }

  function getAgeTierLabel(tier: string | null): string {
    switch (tier) {
      case 'young':
        return 'Age 5-9';
      case 'preteen':
        return 'Age 10-12';
      case 'teen':
        return 'Age 13-15';
      default:
        return 'Unknown';
    }
  }

  function getAgeTierVariant(tier: string | null): 'info' | 'success' | 'warning' {
    switch (tier) {
      case 'young':
        return 'warning';
      case 'preteen':
        return 'info';
      case 'teen':
        return 'success';
      default:
        return 'info';
    }
  }

  function formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function renderItem({ item }: { item: ContactApprovalItem }) {
    const isSelected = selectedIds.has(item.id);
    const isProcessing = processing.has(item.id);

    return React.createElement(
      TouchableOpacity,
      {
        onPress: () => toggleSelect(item.id),
        activeOpacity: 0.7,
        accessibilityLabel: `Contact request from ${item.requester_display_name ?? 'Unknown'} to ${item.target_display_name ?? 'Unknown'}`,
        accessibilityRole: 'checkbox',
        accessibilityState: { checked: isSelected },
      },
      React.createElement(
        Card,
        {
          style: [styles.requestCard, isSelected && styles.requestCardSelected],
        },
        // Header row: checkbox indicator + requester info
        React.createElement(
          View,
          { style: styles.requestHeader },
          React.createElement(
            View,
            { style: [styles.checkbox, isSelected && styles.checkboxSelected] },
            isSelected
              ? React.createElement(Text, { style: styles.checkmark }, '\u2713')
              : null
          ),
          React.createElement(Avatar, {
            name: item.requester_display_name ?? '?',
            size: 'md',
          }),
          React.createElement(
            View,
            { style: styles.requestInfo },
            React.createElement(
              Text,
              { style: styles.requestName },
              item.requester_display_name ?? 'Unknown User'
            ),
            React.createElement(Badge, {
              text: getAgeTierLabel(item.requester_age_tier),
              variant: getAgeTierVariant(item.requester_age_tier),
            })
          )
        ),

        // Target info
        React.createElement(
          View,
          { style: styles.targetRow },
          React.createElement(
            Text,
            { style: styles.targetLabel },
            'Wants to connect with:'
          ),
          React.createElement(
            Text,
            { style: styles.targetName },
            item.target_display_name ?? 'Unknown'
          ),
          item.target_age_tier
            ? React.createElement(Badge, {
                text: getAgeTierLabel(item.target_age_tier),
                variant: getAgeTierVariant(item.target_age_tier),
              })
            : null
        ),

        // Timestamp
        React.createElement(
          Text,
          { style: styles.timestamp },
          `Requested: ${formatDate(item.created_at)}`
        ),

        // Action buttons (per-item)
        React.createElement(
          View,
          { style: styles.actionRow },
          React.createElement(Button, {
            title: 'Deny',
            onPress: () => handleSingleDecision(item.id, 'deny'),
            variant: 'outline',
            size: 'sm',
            disabled: isProcessing || batchProcessing,
            accessibilityLabel: `Deny contact request from ${item.requester_display_name}`,
          }),
          React.createElement(Button, {
            title: 'Approve',
            onPress: () => handleSingleDecision(item.id, 'approve'),
            size: 'sm',
            isLoading: isProcessing,
            disabled: isProcessing || batchProcessing,
            accessibilityLabel: `Approve contact request from ${item.requester_display_name}`,
          })
        )
      )
    );
  }

  // Loading state
  if (state === 'loading' && items.length === 0) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading pending approvals' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  // Error state
  if (state === 'error' && items.length === 0) {
    return React.createElement(
      View,
      { style: styles.centered },
      React.createElement(
        Text,
        { style: styles.errorText, accessibilityRole: 'alert' },
        error
      ),
      React.createElement(
        TouchableOpacity,
        { onPress: loadPending, style: styles.retryButton },
        React.createElement(Text, { style: styles.retryText }, 'Tap to retry')
      )
    );
  }

  const hasSelection = selectedIds.size > 0;

  return React.createElement(
    View,
    { style: styles.container, accessibilityLabel: 'Contact approval requests' },

    // Header
    React.createElement(
      View,
      { style: styles.headerRow },
      React.createElement(
        Text,
        { style: styles.heading, accessibilityRole: 'header' },
        'Contact Approvals'
      ),
      React.createElement(
        Text,
        { style: styles.pendingCount },
        `${items.length} pending`
      )
    ),

    // Batch actions bar
    items.length > 0
      ? React.createElement(
          View,
          { style: styles.batchBar },
          React.createElement(
            TouchableOpacity,
            { onPress: selectAll, accessibilityLabel: 'Select all requests' },
            React.createElement(
              Text,
              { style: styles.selectAllText },
              selectedIds.size === items.length ? 'Deselect All' : 'Select All'
            )
          ),
          hasSelection
            ? React.createElement(
                View,
                { style: styles.batchActions },
                React.createElement(Button, {
                  title: `Deny (${selectedIds.size})`,
                  onPress: () => handleBatchDecision('deny'),
                  variant: 'outline',
                  size: 'sm',
                  disabled: batchProcessing,
                }),
                React.createElement(Button, {
                  title: `Approve (${selectedIds.size})`,
                  onPress: () => handleBatchDecision('approve'),
                  size: 'sm',
                  isLoading: batchProcessing,
                  disabled: batchProcessing,
                })
              )
            : null
        )
      : null,

    // Request list
    React.createElement(FlatList, {
      data: items,
      keyExtractor: (item: ContactApprovalItem) => item.id,
      renderItem,
      contentContainerStyle: styles.listContent,
      refreshControl: React.createElement(RefreshControl, {
        refreshing,
        onRefresh,
        tintColor: colors.primary[600],
      }),
      ListEmptyComponent: React.createElement(
        View,
        { style: styles.emptyContainer },
        React.createElement(
          Text,
          { style: styles.emptyTitle },
          'No Pending Approvals'
        ),
        React.createElement(
          Text,
          { style: styles.emptyText },
          'When your children send contact requests, they will appear here for your review.'
        )
      ),
    })
  );
}

// Exported for testing
export { type ContactApprovalItem, type PendingResponse, type ScreenState };

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
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
  },
  heading: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  pendingCount: {
    fontSize: typography.sizes.sm,
    color: colors.primary[600],
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  batchBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  selectAllText: {
    fontSize: typography.sizes.sm,
    color: colors.primary[700],
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  batchActions: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  listContent: {
    padding: spacing.md,
  },
  requestCard: {
    marginBottom: spacing.sm,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  requestCardSelected: {
    borderColor: colors.primary[400],
  },
  requestHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 4,
    borderWidth: 2,
    borderColor: colors.neutral[300],
    marginRight: spacing.sm,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxSelected: {
    backgroundColor: colors.primary[600],
    borderColor: colors.primary[600],
  },
  checkmark: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
  requestInfo: {
    flex: 1,
    marginLeft: spacing.sm,
  },
  requestName: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    marginBottom: 2,
    fontFamily: typography.fontFamily,
  },
  targetRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 24 + spacing.sm, // align with name after checkbox
    marginBottom: spacing.sm,
    gap: spacing.xs,
  },
  targetLabel: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  targetName: {
    fontSize: typography.sizes.sm,
    fontWeight: '600',
    color: colors.neutral[700],
    fontFamily: typography.fontFamily,
  },
  timestamp: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[400],
    marginLeft: 24 + spacing.sm,
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: spacing.sm,
  },
  emptyContainer: {
    paddingVertical: spacing['2xl'],
    alignItems: 'center',
  },
  emptyTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: '600',
    color: colors.neutral[700],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  emptyText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    textAlign: 'center',
    paddingHorizontal: spacing.lg,
    fontFamily: typography.fontFamily,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.sm,
    textAlign: 'center',
    padding: spacing.md,
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
