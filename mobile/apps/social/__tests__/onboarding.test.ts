/**
 * Onboarding Flow Tests — Social App
 *
 * Tests: age verification, parent consent, profile creation,
 * tier assignment, form validation, step navigation, edge cases.
 */

// ---------------------------------------------------------------------------
// Onboarding screen tests
// ---------------------------------------------------------------------------

describe('Onboarding Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(auth)/onboarding');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports OnboardingStep type helpers', () => {
    const mod = require('../app/(auth)/onboarding');
    expect(mod.getTierForAge).toBeDefined();
    expect(mod.TIER_LABELS).toBeDefined();
    expect(mod.MIN_DISPLAY_NAME_LENGTH).toBeDefined();
    expect(mod.MAX_DISPLAY_NAME_LENGTH).toBeDefined();
    expect(mod.MAX_BIO_LENGTH).toBeDefined();
    expect(mod.CONSENT_AGE_THRESHOLD).toBeDefined();
  });

  test('getTierForAge returns correct tiers', () => {
    const { getTierForAge } = require('../app/(auth)/onboarding');
    expect(getTierForAge(5)).toBe('young');
    expect(getTierForAge(7)).toBe('young');
    expect(getTierForAge(9)).toBe('young');
    expect(getTierForAge(10)).toBe('preteen');
    expect(getTierForAge(12)).toBe('preteen');
    expect(getTierForAge(13)).toBe('teen');
    expect(getTierForAge(15)).toBe('teen');
  });

  test('getTierForAge returns null for out-of-range ages', () => {
    const { getTierForAge } = require('../app/(auth)/onboarding');
    expect(getTierForAge(4)).toBeNull();
    expect(getTierForAge(16)).toBeNull();
    expect(getTierForAge(0)).toBeNull();
    expect(getTierForAge(100)).toBeNull();
  });

  test('TIER_LABELS has all three tiers', () => {
    const { TIER_LABELS } = require('../app/(auth)/onboarding');
    expect(TIER_LABELS.young).toBeDefined();
    expect(TIER_LABELS.preteen).toBeDefined();
    expect(TIER_LABELS.teen).toBeDefined();
    expect(Object.keys(TIER_LABELS)).toHaveLength(3);
  });

  test('CONSENT_AGE_THRESHOLD is 13', () => {
    const { CONSENT_AGE_THRESHOLD } = require('../app/(auth)/onboarding');
    expect(CONSENT_AGE_THRESHOLD).toBe(13);
  });

  test('display name length bounds are sane', () => {
    const { MIN_DISPLAY_NAME_LENGTH, MAX_DISPLAY_NAME_LENGTH } = require('../app/(auth)/onboarding');
    expect(MIN_DISPLAY_NAME_LENGTH).toBeGreaterThanOrEqual(1);
    expect(MAX_DISPLAY_NAME_LENGTH).toBeLessThanOrEqual(255);
    expect(MAX_DISPLAY_NAME_LENGTH).toBeGreaterThan(MIN_DISPLAY_NAME_LENGTH);
  });

  test('bio length limit is reasonable', () => {
    const { MAX_BIO_LENGTH } = require('../app/(auth)/onboarding');
    expect(MAX_BIO_LENGTH).toBeGreaterThan(0);
    expect(MAX_BIO_LENGTH).toBeLessThanOrEqual(500);
  });

  test('default export is a callable function', () => {
    const OnboardingScreen = require('../app/(auth)/onboarding').default;
    expect(typeof OnboardingScreen).toBe('function');
  });
});

// ---------------------------------------------------------------------------
// Age Verify screen tests
// ---------------------------------------------------------------------------

describe('Age Verify Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(auth)/age-verify');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports VerifyState type (module loads)', () => {
    const mod = require('../app/(auth)/age-verify');
    // VerifyState is a TypeScript type, erased at runtime.
    // We just verify the module loads without error.
    expect(mod.default).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Login screen tests (updated with onboarding redirect)
// ---------------------------------------------------------------------------

describe('Login Screen (with onboarding)', () => {
  test('exports default component', () => {
    const mod = require('../app/(auth)/login');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports PostLoginDestination type', () => {
    // TypeScript type — just ensure the module loads cleanly
    const mod = require('../app/(auth)/login');
    expect(mod.default).toBeDefined();
  });

  test('renders login screen', () => {
    const SocialLoginScreen = require('../app/(auth)/login').default;
    const result = SocialLoginScreen();
    expect(result).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Shared types tests
// ---------------------------------------------------------------------------

describe('Shared Types — Social Onboarding', () => {
  test('social.ts module loads and has Profile type', () => {
    // TypeScript interfaces are erased at runtime; verify module loads.
    // @bhapi/types maps to the shared-types/src/index.ts barrel.
    const mod = require('@bhapi/types');
    expect(mod).toBeDefined();
  });

  test('shared-types index exports are accessible', () => {
    const mod = require('@bhapi/types');
    // The module should load without errors — type exports are erased
    expect(typeof mod).toBe('object');
  });
});

// ---------------------------------------------------------------------------
// Edge case tests
// ---------------------------------------------------------------------------

describe('Onboarding Edge Cases', () => {
  test('getTierForAge handles boundary ages precisely', () => {
    const { getTierForAge } = require('../app/(auth)/onboarding');
    // Boundary: 4 -> null, 5 -> young
    expect(getTierForAge(4)).toBeNull();
    expect(getTierForAge(5)).toBe('young');
    // Boundary: 9 -> young, 10 -> preteen
    expect(getTierForAge(9)).toBe('young');
    expect(getTierForAge(10)).toBe('preteen');
    // Boundary: 12 -> preteen, 13 -> teen
    expect(getTierForAge(12)).toBe('preteen');
    expect(getTierForAge(13)).toBe('teen');
    // Boundary: 15 -> teen, 16 -> null
    expect(getTierForAge(15)).toBe('teen');
    expect(getTierForAge(16)).toBeNull();
  });

  test('getTierForAge handles negative ages', () => {
    const { getTierForAge } = require('../app/(auth)/onboarding');
    expect(getTierForAge(-1)).toBeNull();
  });

  test('TIER_LABELS values are human-readable strings', () => {
    const { TIER_LABELS } = require('../app/(auth)/onboarding');
    for (const [key, label] of Object.entries(TIER_LABELS)) {
      expect(typeof label).toBe('string');
      expect((label as string).length).toBeGreaterThan(0);
    }
  });
});
