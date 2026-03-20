import { getInitials, avatarSizes } from '../src/Avatar';

describe('Avatar', () => {
  describe('getInitials', () => {
    test('single name returns first letter', () => {
      expect(getInitials('Alice')).toBe('A');
    });

    test('two names returns first and last initials', () => {
      expect(getInitials('Alice Smith')).toBe('AS');
    });

    test('three names returns first and last initials', () => {
      expect(getInitials('Alice Marie Smith')).toBe('AS');
    });

    test('empty string returns ?', () => {
      expect(getInitials('')).toBe('?');
    });

    test('whitespace only returns ?', () => {
      expect(getInitials('   ')).toBe('?');
    });

    test('lowercase is uppercased', () => {
      expect(getInitials('alice smith')).toBe('AS');
    });

    test('single character name', () => {
      expect(getInitials('A')).toBe('A');
    });
  });

  describe('sizes', () => {
    test('sm is 32px', () => {
      expect(avatarSizes.sm).toBe(32);
    });

    test('md is 48px', () => {
      expect(avatarSizes.md).toBe(48);
    });

    test('lg is 64px', () => {
      expect(avatarSizes.lg).toBe(64);
    });
  });
});
