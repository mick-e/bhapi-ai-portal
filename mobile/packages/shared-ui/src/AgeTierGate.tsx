/**
 * AgeTierGate — Conditionally renders children based on age-tier permissions.
 *
 * If the user's age tier grants the required permission, children are rendered.
 * If denied, shows a friendly lock explanation with an optional "Ask parent" button.
 *
 * Uses the permission matrix from @bhapi/config (AGE_TIERS, FEATURE_DESCRIPTIONS)
 * and the TIER_PERMISSIONS mapping to determine access.
 */
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors, spacing, typography, FEATURE_DESCRIPTIONS } from '@bhapi/config';
import type { AgeTier, FeatureDescription } from '@bhapi/config';

/**
 * Permission matrix mirroring src/age_tier/rules.py TIER_PERMISSIONS.
 * Only boolean permissions are included (non-boolean like max_contacts are not gateable).
 */
const TIER_PERMISSIONS: Record<AgeTier, Record<string, boolean>> = {
  young: {
    can_post: true,
    can_comment: true,
    can_message: false,
    can_like: true,
    can_follow: true,
    can_create_group_chat: false,
    can_search_users: false,
    can_upload_image: true,
    can_upload_video: false,
    can_use_ai_chat: false,
    can_share_location: false,
    can_add_contacts: false,
  },
  preteen: {
    can_post: true,
    can_comment: true,
    can_message: true,
    can_like: true,
    can_follow: true,
    can_create_group_chat: false,
    can_search_users: true,
    can_upload_image: true,
    can_upload_video: false,
    can_use_ai_chat: false,
    can_share_location: false,
    can_add_contacts: true,
  },
  teen: {
    can_post: true,
    can_comment: true,
    can_message: true,
    can_like: true,
    can_follow: true,
    can_create_group_chat: true,
    can_search_users: true,
    can_upload_image: true,
    can_upload_video: true,
    can_use_ai_chat: true,
    can_share_location: false,
    can_add_contacts: true,
  },
};

export interface AgeTierGateProps {
  /** The permission to check (e.g. "can_message", "can_upload_video") */
  permission: string;
  /** The current user's age tier */
  ageTier: AgeTier;
  /** Content to render when permission is granted */
  children: React.ReactNode;
  /** Optional callback when "Ask parent" button is pressed */
  onUnlockRequest?: () => void;
  /** Optional override for the lock message */
  lockMessage?: string;
  /** Optional custom accessibility label for the locked state */
  accessibilityLabel?: string;
}

/**
 * Check whether a permission is granted for a given age tier.
 * Exported for unit testing.
 */
export function checkTierPermission(ageTier: AgeTier, permission: string): boolean {
  const tierPerms = TIER_PERMISSIONS[ageTier];
  if (!tierPerms) return false;
  return tierPerms[permission] ?? false;
}

/**
 * Get the feature description for a permission.
 * Exported for unit testing.
 */
export function getFeatureDescription(permission: string): FeatureDescription | undefined {
  return FEATURE_DESCRIPTIONS[permission];
}

/**
 * Build the default lock message for a permission.
 */
function getDefaultLockMessage(permission: string): string {
  const desc = FEATURE_DESCRIPTIONS[permission];
  if (desc) return desc.lockMessage;
  return "You'll be able to do this when you're older!";
}

export function AgeTierGate({
  permission,
  ageTier,
  children,
  onUnlockRequest,
  lockMessage,
  accessibilityLabel,
}: AgeTierGateProps) {
  const allowed = checkTierPermission(ageTier, permission);

  if (allowed) {
    return React.createElement(React.Fragment, null, children);
  }

  const desc = FEATURE_DESCRIPTIONS[permission];
  const message = lockMessage ?? getDefaultLockMessage(permission);
  const showAskParent = desc?.parentCanUnlock === true && onUnlockRequest != null;

  return React.createElement(
    View,
    {
      style: styles.container,
      accessibilityLabel: accessibilityLabel ?? `${desc?.label ?? permission} is locked`,
      accessibilityRole: 'alert',
    },
    // Lock icon
    React.createElement(
      Text,
      { style: styles.lockIcon, accessibilityElementsHidden: true },
      '\uD83D\uDD12'
    ),
    // Lock message
    React.createElement(
      Text,
      { style: styles.lockMessage },
      message
    ),
    // Unlock age hint
    desc
      ? React.createElement(
          Text,
          { style: styles.unlockAge },
          `Unlocks at age ${desc.unlockAge}`
        )
      : null,
    // "Ask parent to unlock" button
    showAskParent
      ? React.createElement(
          TouchableOpacity,
          {
            style: styles.askParentButton,
            onPress: onUnlockRequest,
            accessibilityLabel: 'Ask parent to unlock',
            accessibilityRole: 'button',
          },
          React.createElement(
            Text,
            { style: styles.askParentText },
            'Ask parent to unlock'
          )
        )
      : null
  );
}

export const ageTierGateStyles = {
  borderRadius: 12,
  minHeight: 44,
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.neutral[100],
    borderRadius: 12,
    padding: spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  lockIcon: {
    fontSize: 32,
    marginBottom: spacing.sm,
  },
  lockMessage: {
    fontSize: typography.sizes.base,
    color: colors.neutral[700],
    textAlign: 'center',
    lineHeight: 22,
    fontFamily: typography.fontFamily,
    marginBottom: spacing.xs,
  },
  unlockAge: {
    fontSize: typography.sizes.sm,
    color: colors.neutral[500],
    textAlign: 'center',
    fontFamily: typography.fontFamily,
    marginBottom: spacing.md,
  },
  askParentButton: {
    backgroundColor: colors.primary[600],
    borderRadius: 8,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    minHeight: 44,
    minWidth: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  askParentText: {
    color: '#FFFFFF',
    fontSize: typography.sizes.base,
    fontWeight: '600',
    fontFamily: typography.fontFamily,
  },
});
