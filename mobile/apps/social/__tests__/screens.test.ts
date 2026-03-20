/**
 * Social App Screen Tests
 *
 * Verifies that all screen modules export default components
 * and basic structure is correct.
 */

describe('Social App Screens', () => {
  // Task 20: Social App Shells
  describe('Root Layout', () => {
    test('exports default component', () => {
      const mod = require('../app/_layout');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });
  });

  describe('Index (redirect)', () => {
    test('exports default component', () => {
      const mod = require('../app/index');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });
  });

  describe('Login Screen', () => {
    test('exports default component', () => {
      const mod = require('../app/(auth)/login');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });
  });

  describe('Feed Screen', () => {
    test('exports default component', () => {
      const mod = require('../app/(feed)/index');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });
  });

  describe('Chat List Screen', () => {
    test('exports default component', () => {
      const mod = require('../app/(chat)/index');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });
  });

  describe('Profile Screen', () => {
    test('exports default component', () => {
      const mod = require('../app/(profile)/index');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });
  });

  describe('Settings Screen', () => {
    test('exports default component', () => {
      const mod = require('../app/(settings)/index');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });
  });
});
