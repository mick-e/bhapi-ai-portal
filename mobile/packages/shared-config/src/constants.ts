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
