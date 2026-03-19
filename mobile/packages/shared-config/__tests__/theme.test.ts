import { colors, typography, spacing, AGE_TIERS, MEMBER_LIMITS } from '../src';

describe('theme', () => {
  test('primary color is Bhapi orange', () => {
    expect(colors.primary[500]).toBe('#FF6B35');
  });

  test('accent color is Bhapi teal', () => {
    expect(colors.accent[500]).toBe('#0D9488');
  });

  test('font family is Inter', () => {
    expect(typography.fontFamily).toBe('Inter');
  });

  test('spacing scale is consistent', () => {
    expect(spacing.sm).toBeLessThan(spacing.md);
    expect(spacing.md).toBeLessThan(spacing.lg);
  });

  test('age tiers cover 5-15 range', () => {
    expect(AGE_TIERS.YOUNG.min).toBe(5);
    expect(AGE_TIERS.TEEN.max).toBe(15);
  });

  test('member limits match pricing tiers', () => {
    expect(MEMBER_LIMITS.FREE).toBe(5);
    expect(MEMBER_LIMITS.FAMILY_PLUS).toBe(10);
    expect(MEMBER_LIMITS.SCHOOL).toBe(Infinity);
  });
});
