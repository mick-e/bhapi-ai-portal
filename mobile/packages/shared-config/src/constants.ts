export const API_VERSION = 'v1';

export const AGE_TIERS = {
  YOUNG: { min: 5, max: 9, label: 'young' },
  PRETEEN: { min: 10, max: 12, label: 'preteen' },
  TEEN: { min: 13, max: 15, label: 'teen' },
} as const;

export const MEMBER_LIMITS = {
  FREE: 5,
  FAMILY: 5,
  FAMILY_PLUS: 10,
  SCHOOL: Infinity,
  ENTERPRISE: Infinity,
} as const;

export const SUBSCRIPTION_TIERS = {
  FREE: 'free',
  FAMILY: 'family',
  FAMILY_PLUS: 'family_plus',
  SCHOOL: 'school',
  ENTERPRISE: 'enterprise',
} as const;

export type SubscriptionTier = typeof SUBSCRIPTION_TIERS[keyof typeof SUBSCRIPTION_TIERS];
export type AgeTier = typeof AGE_TIERS[keyof typeof AGE_TIERS]['label'];

/**
 * Feature descriptions for age-tier gating UX.
 * Maps permission names to child-friendly explanations and unlock ages.
 */
export interface FeatureDescription {
  /** Child-friendly explanation of why the feature is locked */
  lockMessage: string;
  /** Age when the feature becomes available */
  unlockAge: number;
  /** Short label for the feature */
  label: string;
  /** Whether parents can request early unlock */
  parentCanUnlock: boolean;
}

export const FEATURE_DESCRIPTIONS: Record<string, FeatureDescription> = {
  can_message: {
    lockMessage: 'Messaging unlocks at age 10. Keep having fun with posts and comments!',
    unlockAge: 10,
    label: 'Messaging',
    parentCanUnlock: true,
  },
  can_search_users: {
    lockMessage: 'Searching for friends unlocks at age 10. Ask a parent to help you connect!',
    unlockAge: 10,
    label: 'Search Users',
    parentCanUnlock: true,
  },
  can_add_contacts: {
    lockMessage: 'Adding contacts unlocks at age 10. Your parent can add friends for you!',
    unlockAge: 10,
    label: 'Add Contacts',
    parentCanUnlock: true,
  },
  can_upload_video: {
    lockMessage: 'Video uploads unlock at age 13. You can still share images and text!',
    unlockAge: 13,
    label: 'Upload Video',
    parentCanUnlock: false,
  },
  can_create_group_chat: {
    lockMessage: 'Group chats unlock at age 13. You can chat one-on-one for now!',
    unlockAge: 13,
    label: 'Group Chat',
    parentCanUnlock: false,
  },
  can_use_ai_chat: {
    lockMessage: 'AI chat unlocks at age 13. There are lots of other fun things to explore!',
    unlockAge: 13,
    label: 'AI Chat',
    parentCanUnlock: false,
  },
  can_share_location: {
    lockMessage: 'Location sharing is not available yet. Your safety comes first!',
    unlockAge: 16,
    label: 'Share Location',
    parentCanUnlock: false,
  },
} as const;
