/**
 * Children / Group Members Screen
 *
 * Shows member list with role badges, safety scores, and add member flow.
 * API: GET /api/v1/groups/:group_id/members
 * API: POST /api/v1/groups/:group_id/invitations { email, role }
 *
 * Family member cap is 5 (enforced server-side).
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Card, Badge, Avatar, Button, Input } from '@bhapi/ui';
import { MEMBER_LIMITS } from '@bhapi/config';

interface GroupMember {
  id: string;
  name: string;
  email: string | null;
  role: 'parent' | 'child';
  safety_score: number | null;
  last_active: string | null;
  avatar_url: string | null;
}

type ScreenState = 'loading' | 'loaded' | 'error';

export default function ChildrenScreen() {
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [state, setState] = useState<ScreenState>('loading');
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviting, setInviting] = useState(false);

  useEffect(() => {
    loadMembers();
  }, []);

  async function loadMembers() {
    try {
      setState('loading');
      // API call: GET /api/v1/groups/:group_id/members
      // const response = await apiClient.get<GroupMember[]>(`/api/v1/groups/${groupId}/members`);
      // setMembers(response);
      setState('loaded');
    } catch (e: any) {
      setState('error');
      setError(e?.message ?? 'Failed to load family members.');
    }
  }

  async function handleInvite() {
    if (!inviteEmail.trim()) return;

    try {
      setInviting(true);
      // API call: POST /api/v1/groups/:group_id/invitations
      // await apiClient.post(`/api/v1/groups/${groupId}/invitations`, {
      //   email: inviteEmail.trim(),
      //   role: 'child',
      // });
      setInviteEmail('');
      setShowAddForm(false);
      await loadMembers();
    } catch (e: any) {
      setError(e?.message ?? 'Failed to send invitation.');
    } finally {
      setInviting(false);
    }
  }

  function renderMember({ item }: { item: GroupMember }) {
    return React.createElement(
      Card,
      {
        style: styles.memberCard,
        accessibilityLabel: `${item.name}, ${item.role}`,
      },
      React.createElement(
        View,
        { style: styles.memberRow },
        React.createElement(Avatar, {
          name: item.name,
          size: 'md',
        }),
        React.createElement(
          View,
          { style: styles.memberInfo },
          React.createElement(
            Text,
            { style: styles.memberName },
            item.name
          ),
          React.createElement(Badge, {
            text: item.role,
            variant: item.role === 'parent' ? 'info' : 'success',
          }),
          item.last_active
            ? React.createElement(
                Text,
                { style: styles.lastActive },
                `Last active: ${item.last_active}`
              )
            : null
        ),
        item.safety_score !== null
          ? React.createElement(
              View,
              { style: styles.scoreContainer, accessibilityLabel: `Safety score: ${item.safety_score}` },
              React.createElement(
                Text,
                {
                  style: [
                    styles.scoreValue,
                    {
                      color: item.safety_score >= 70
                        ? colors.semantic.success
                        : item.safety_score >= 40
                          ? colors.semantic.warning
                          : colors.semantic.error,
                    },
                  ],
                },
                String(item.safety_score)
              ),
              React.createElement(
                Text,
                { style: styles.scoreLabel },
                'Safety'
              )
            )
          : null
      )
    );
  }

  if (state === 'loading' && members.length === 0) {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading members' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  if (state === 'error' && members.length === 0) {
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
        { onPress: loadMembers, style: styles.retryButton },
        React.createElement(Text, { style: styles.retryText }, 'Tap to retry')
      )
    );
  }

  const atMemberCap = members.length >= MEMBER_LIMITS.FAMILY;

  return React.createElement(
    View,
    { style: styles.container, accessibilityLabel: 'Family members' },
    React.createElement(
      View,
      { style: styles.headerRow },
      React.createElement(
        Text,
        { style: styles.heading, accessibilityRole: 'header' },
        'Family Members'
      ),
      React.createElement(
        Text,
        { style: styles.memberCount },
        `${members.length} / ${MEMBER_LIMITS.FAMILY}`
      )
    ),

    // Add member form
    showAddForm
      ? React.createElement(
          Card,
          { style: styles.addCard, accessibilityLabel: 'Add family member' },
          React.createElement(Input, {
            label: 'Email Address',
            placeholder: 'child@example.com',
            value: inviteEmail,
            onChangeText: setInviteEmail,
            keyboardType: 'email-address',
            autoCapitalize: 'none',
            accessibilityLabel: 'Invite email address',
          }),
          React.createElement(
            View,
            { style: styles.addActions },
            React.createElement(Button, {
              title: 'Cancel',
              onPress: () => {
                setShowAddForm(false);
                setInviteEmail('');
              },
              variant: 'outline',
              size: 'sm',
            }),
            React.createElement(Button, {
              title: 'Send Invite',
              onPress: handleInvite,
              isLoading: inviting,
              disabled: inviting || !inviteEmail.trim(),
              size: 'sm',
            })
          )
        )
      : null,

    // Add member button
    !showAddForm && !atMemberCap
      ? React.createElement(Button, {
          title: 'Add Family Member',
          onPress: () => setShowAddForm(true),
          variant: 'outline',
          style: styles.addButton,
          accessibilityLabel: 'Add a family member',
        })
      : null,
    atMemberCap && !showAddForm
      ? React.createElement(
          Text,
          { style: styles.capText },
          'Family member limit reached (5 members).'
        )
      : null,

    // Error message
    error && state !== 'error'
      ? React.createElement(
          Text,
          { style: styles.errorText, accessibilityRole: 'alert' },
          error
        )
      : null,

    // Member list
    React.createElement(FlatList, {
      data: members,
      keyExtractor: (item: GroupMember) => item.id,
      renderItem: renderMember,
      contentContainerStyle: styles.listContent,
      ListEmptyComponent: React.createElement(
        View,
        { style: styles.emptyContainer },
        React.createElement(
          Text,
          { style: styles.emptyText },
          'No family members yet. Add a child to start monitoring.'
        )
      ),
    })
  );
}

// Exported for testing
export { type GroupMember, type ScreenState };

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
  },
  heading: {
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    color: colors.neutral[900],
    fontFamily: typography.fontFamily,
  },
  memberCount: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  addButton: {
    marginHorizontal: spacing.md,
    marginVertical: spacing.sm,
  },
  addCard: {
    marginHorizontal: spacing.md,
    marginVertical: spacing.sm,
  },
  addActions: {
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'flex-end',
  },
  capText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    textAlign: 'center',
    paddingVertical: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  listContent: {
    padding: spacing.md,
  },
  memberCard: {
    marginBottom: spacing.sm,
  },
  memberRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  memberInfo: {
    flex: 1,
    marginLeft: spacing.md,
  },
  memberName: {
    fontSize: typography.sizes.base,
    fontWeight: '600',
    color: colors.neutral[900],
    marginBottom: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  lastActive: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    marginTop: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  scoreContainer: {
    alignItems: 'center',
    marginLeft: spacing.sm,
  },
  scoreValue: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
  scoreLabel: {
    fontSize: typography.sizes.xs,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  emptyContainer: {
    paddingVertical: spacing['2xl'],
    alignItems: 'center',
  },
  emptyText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    textAlign: 'center',
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
