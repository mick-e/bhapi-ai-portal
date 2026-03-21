/**
 * Contact Request Detail Screen
 *
 * Shows:
 * - Requester profile preview (avatar, name, bio, age tier)
 * - Mutual contacts count
 * - Accept/reject buttons
 * - Parent approval badge (for under-13 requesters)
 *
 * API:
 *   GET /api/v1/social/profiles/{userId} — requester profile
 *   PATCH /api/v1/contacts/{contactId}/respond — accept/reject
 *   GET /api/v1/contacts/?status=accepted — mutual contacts check
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
  StyleSheet,
} from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';

interface RequesterProfile {
  user_id: string;
  display_name: string;
  avatar_url: string | null;
  bio: string | null;
  age_tier: string;
}

interface ContactRequestDetail {
  id: string;
  requester_id: string;
  target_id: string;
  status: string;
  parent_approval_status: string;
  created_at: string;
}

type RequestState = 'loading' | 'loaded' | 'error' | 'processing' | 'done';

export default function ContactRequestScreen() {
  const [requestState, setRequestState] = useState<RequestState>('loading');
  const [profile, setProfile] = useState<RequesterProfile | null>(null);
  const [contact, setContact] = useState<ContactRequestDetail | null>(null);
  const [mutualCount, setMutualCount] = useState(0);
  const [error, setError] = useState('');
  const [decision, setDecision] = useState<'accepted' | 'rejected' | null>(null);

  // In real implementation, contactId comes from route params
  // const { contactId } = useLocalSearchParams();

  useEffect(() => {
    loadRequest();
  }, []);

  async function loadRequest() {
    setRequestState('loading');
    try {
      // API: fetch contact detail and requester profile
      // const contactResp = await apiClient.get(`/api/v1/contacts/${contactId}`);
      // const profileResp = await apiClient.get(`/api/v1/social/profiles/${contactResp.requester_id}`);
      // setContact(contactResp);
      // setProfile(profileResp);
      // setMutualCount(await fetchMutualContacts(contactResp.requester_id));

      // Placeholder
      setContact(null);
      setProfile(null);
      setMutualCount(0);
      setRequestState('loaded');
    } catch (e: any) {
      setRequestState('error');
      setError(e?.message ?? 'Could not load request.');
    }
  }

  async function handleRespond(action: 'accept' | 'reject') {
    if (!contact) return;
    setRequestState('processing');
    try {
      // API: PATCH /api/v1/contacts/{contactId}/respond { action }
      // await apiClient.patch(`/api/v1/contacts/${contact.id}/respond`, { action });
      setDecision(action === 'accept' ? 'accepted' : 'rejected');
      setRequestState('done');
    } catch (e: any) {
      setRequestState('error');
      setError(e?.message ?? `Could not ${action} request.`);
    }
  }

  if (requestState === 'loading') {
    return React.createElement(
      View,
      { style: styles.centered, accessibilityLabel: 'Loading request' },
      React.createElement(ActivityIndicator, {
        size: 'large',
        color: colors.primary[600],
      })
    );
  }

  if (requestState === 'error') {
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
        { onPress: loadRequest, style: styles.retryButton },
        React.createElement(Text, { style: styles.retryText }, 'Try again')
      )
    );
  }

  if (requestState === 'done') {
    return React.createElement(
      View,
      { style: styles.centered },
      React.createElement(
        Text,
        { style: styles.doneTitle },
        decision === 'accepted' ? 'Request Accepted!' : 'Request Declined'
      ),
      React.createElement(
        Text,
        { style: styles.doneText },
        decision === 'accepted'
          ? `You are now connected with ${profile?.display_name ?? 'this user'}.`
          : 'The request has been declined.'
      )
    );
  }

  const requiresParentApproval = contact?.parent_approval_status === 'pending';
  const displayName = profile?.display_name ?? 'Unknown User';
  const initials = displayName
    .split(/\s+/)
    .map((w: string) => w.charAt(0))
    .join('')
    .toUpperCase()
    .slice(0, 2);

  return React.createElement(
    ScrollView,
    {
      style: styles.container,
      contentContainerStyle: styles.content,
      accessibilityLabel: `Contact request from ${displayName}`,
    },

    // Profile preview
    React.createElement(
      View,
      { style: styles.profileCard },
      React.createElement(
        View,
        { style: styles.avatar },
        React.createElement(Text, { style: styles.avatarText }, initials)
      ),
      React.createElement(
        Text,
        { style: styles.displayName },
        displayName
      ),
      profile?.bio
        ? React.createElement(
            Text,
            { style: styles.bio },
            profile.bio
          )
        : null,

      // Age tier badge
      profile?.age_tier
        ? React.createElement(
            View,
            { style: styles.ageTierBadge },
            React.createElement(
              Text,
              { style: styles.ageTierText },
              profile.age_tier === 'young'
                ? 'Age 5-9'
                : profile.age_tier === 'preteen'
                  ? 'Age 10-12'
                  : 'Age 13-15'
            )
          )
        : null,

      // Parent approval badge
      requiresParentApproval
        ? React.createElement(
            View,
            { style: styles.parentBadge },
            React.createElement(
              Text,
              { style: styles.parentBadgeText },
              'Needs parent approval'
            )
          )
        : null
    ),

    // Mutual contacts
    React.createElement(
      View,
      { style: styles.mutualSection },
      React.createElement(
        Text,
        { style: styles.mutualText },
        mutualCount > 0
          ? `${mutualCount} mutual contact${mutualCount === 1 ? '' : 's'}`
          : 'No mutual contacts'
      )
    ),

    // Action buttons
    React.createElement(
      View,
      { style: styles.actions },
      React.createElement(
        TouchableOpacity,
        {
          style: styles.rejectButton,
          onPress: () => handleRespond('reject'),
          disabled: requestState === 'processing',
          accessibilityLabel: `Decline request from ${displayName}`,
          accessibilityRole: 'button',
        },
        React.createElement(
          Text,
          { style: styles.rejectText },
          'Decline'
        )
      ),
      React.createElement(
        TouchableOpacity,
        {
          style: [
            styles.acceptButton,
            requestState === 'processing' ? styles.buttonDisabled : null,
          ],
          onPress: () => handleRespond('accept'),
          disabled: requestState === 'processing',
          accessibilityLabel: requiresParentApproval
            ? `Request parent approval for ${displayName}`
            : `Accept request from ${displayName}`,
          accessibilityRole: 'button',
        },
        requestState === 'processing'
          ? React.createElement(ActivityIndicator, {
              size: 'small',
              color: '#FFFFFF',
            })
          : React.createElement(
              Text,
              { style: styles.acceptText },
              requiresParentApproval ? 'Request Approval' : 'Accept'
            )
      )
    )
  );
}

// Exported for testing
export { type RequesterProfile, type ContactRequestDetail, type RequestState };

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  content: {
    padding: spacing.lg,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
    backgroundColor: colors.neutral[50],
  },
  profileCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: spacing.xl,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    marginBottom: spacing.lg,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.accent[500],
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: typography.sizes['2xl'],
    fontWeight: '700',
    fontFamily: typography.fontFamily,
  },
  displayName: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.neutral[900],
    marginBottom: spacing.xs,
    fontFamily: typography.fontFamily,
  },
  bio: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  ageTierBadge: {
    backgroundColor: colors.primary[50],
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 12,
    marginBottom: spacing.sm,
  },
  ageTierText: {
    fontSize: typography.sizes.xs,
    color: colors.primary[700],
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  parentBadge: {
    backgroundColor: '#FEF3C7',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 12,
  },
  parentBadgeText: {
    fontSize: typography.sizes.xs,
    color: '#92400E',
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  mutualSection: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    padding: spacing.md,
    marginBottom: spacing.lg,
    alignItems: 'center',
  },
  mutualText: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    fontFamily: typography.fontFamily,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  rejectButton: {
    flex: 1,
    paddingVertical: spacing.md,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    alignItems: 'center',
    minHeight: 48,
    justifyContent: 'center',
  },
  rejectText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  acceptButton: {
    flex: 1,
    paddingVertical: spacing.md,
    borderRadius: 8,
    backgroundColor: colors.primary[600],
    alignItems: 'center',
    minHeight: 48,
    justifyContent: 'center',
  },
  acceptText: {
    fontSize: typography.sizes.base,
    color: '#FFFFFF',
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  errorText: {
    color: colors.semantic.error,
    fontSize: typography.sizes.base,
    textAlign: 'center',
    marginBottom: spacing.md,
    fontFamily: typography.fontFamily,
  },
  retryButton: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  retryText: {
    color: colors.primary[700],
    fontSize: typography.sizes.base,
    fontWeight: '500',
    fontFamily: typography.fontFamily,
  },
  doneTitle: {
    fontSize: typography.sizes.xl,
    fontWeight: '700',
    color: colors.neutral[900],
    marginBottom: spacing.sm,
    fontFamily: typography.fontFamily,
  },
  doneText: {
    fontSize: typography.sizes.base,
    color: colors.neutral[500],
    textAlign: 'center',
    fontFamily: typography.fontFamily,
  },
});
