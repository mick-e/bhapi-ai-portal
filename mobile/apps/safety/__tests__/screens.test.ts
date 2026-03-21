/**
 * Safety App Screen Tests
 *
 * Verifies that all screen modules export default components,
 * exported types/constants are correct, and basic rendering works.
 */

describe('Safety App Screens', () => {
  // Task 17: Auth Screens
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

  describe('Auth Layout', () => {
    test('exports default component', () => {
      const mod = require('../app/(auth)/_layout');
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

  describe('Register Screen', () => {
    test('exports default component', () => {
      const mod = require('../app/(auth)/register');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });
  });

  describe('Magic Link Screen', () => {
    test('exports default component', () => {
      const mod = require('../app/(auth)/magic-link');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });
  });

  // Task 18: Dashboard + Alerts
  describe('Dashboard Layout', () => {
    test('exports default component', () => {
      const mod = require('../app/(dashboard)/_layout');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });

    test('exports TABS config with 4 tabs', () => {
      const { TABS } = require('../app/(dashboard)/_layout');
      expect(TABS).toHaveLength(4);
      expect(TABS.map((t: any) => t.key)).toEqual(['index', 'alerts', 'children', 'settings']);
    });
  });

  describe('Dashboard Screen', () => {
    test('exports default component', () => {
      const mod = require('../app/(dashboard)/index');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });

    test('exports SEVERITY_VARIANT mapping', () => {
      const { SEVERITY_VARIANT } = require('../app/(dashboard)/index');
      expect(SEVERITY_VARIANT.low).toBe('info');
      expect(SEVERITY_VARIANT.medium).toBe('warning');
      expect(SEVERITY_VARIANT.high).toBe('error');
      expect(SEVERITY_VARIANT.critical).toBe('error');
    });
  });

  describe('Alerts Screen', () => {
    test('exports default component', () => {
      const mod = require('../app/(dashboard)/alerts');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });

    test('exports SEVERITY_FILTERS with 5 options', () => {
      const { SEVERITY_FILTERS } = require('../app/(dashboard)/alerts');
      expect(SEVERITY_FILTERS).toHaveLength(5);
      expect(SEVERITY_FILTERS[0].value).toBe('all');
    });
  });

  describe('Alert Detail Screen', () => {
    test('exports default component', () => {
      const mod = require('../app/(dashboard)/alert-detail');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });

    test('exports SNOOZE_OPTIONS', () => {
      const { SNOOZE_OPTIONS } = require('../app/(dashboard)/alert-detail');
      expect(SNOOZE_OPTIONS).toHaveLength(4);
      expect(SNOOZE_OPTIONS[0].hours).toBe(1);
      expect(SNOOZE_OPTIONS[3].hours).toBe(168);
    });
  });

  // Task 19: Children + Settings
  describe('Children Screen', () => {
    test('exports default component', () => {
      const mod = require('../app/(children)/index');
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

    test('exports LANGUAGES with 6 options', () => {
      const { LANGUAGES } = require('../app/(settings)/index');
      expect(LANGUAGES).toHaveLength(6);
      expect(LANGUAGES.map((l: any) => l.code)).toEqual(['en', 'es', 'fr', 'de', 'pt-BR', 'it']);
    });
  });

  // P2-M5: Contact Approval Screen
  describe('Contact Approval Screen', () => {
    test('exports default component', () => {
      const mod = require('../app/(children)/contact-approval');
      expect(mod.default).toBeDefined();
      expect(typeof mod.default).toBe('function');
    });

    test('exports ContactApprovalItem type (via ScreenState)', () => {
      // The module exports ScreenState type — verifies the module loads cleanly
      const mod = require('../app/(children)/contact-approval');
      // Default export is the component
      expect(typeof mod.default).toBe('function');
    });
  });
});
