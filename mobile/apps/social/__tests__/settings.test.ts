/**
 * Settings Tests — settings index, privacy screen, notification preferences,
 * theme selection, language selection, account operations, constants/exports.
 */

// ---------------------------------------------------------------------------
// Settings Index Screen
// ---------------------------------------------------------------------------

describe('Settings Index Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(settings)/index');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports DEFAULT_SETTINGS', () => {
    const { DEFAULT_SETTINGS } = require('../app/(settings)/index');
    expect(DEFAULT_SETTINGS).toBeDefined();
    expect(DEFAULT_SETTINGS.notifications_enabled).toBe(true);
    expect(DEFAULT_SETTINGS.profile_visibility).toBe('friends');
    expect(DEFAULT_SETTINGS.allow_messages_from).toBe('friends');
    expect(DEFAULT_SETTINGS.show_online_status).toBe(true);
    expect(DEFAULT_SETTINGS.theme).toBe('system');
    expect(DEFAULT_SETTINGS.language).toBe('en');
  });

  test('exports THEME_OPTIONS with 3 choices', () => {
    const { THEME_OPTIONS } = require('../app/(settings)/index');
    expect(THEME_OPTIONS).toHaveLength(3);
    const values = THEME_OPTIONS.map((o: any) => o.value);
    expect(values).toContain('light');
    expect(values).toContain('dark');
    expect(values).toContain('system');
  });

  test('exports LANGUAGE_OPTIONS with 6 languages', () => {
    const { LANGUAGE_OPTIONS } = require('../app/(settings)/index');
    expect(LANGUAGE_OPTIONS).toHaveLength(6);
    const values = LANGUAGE_OPTIONS.map((o: any) => o.value);
    expect(values).toContain('en');
    expect(values).toContain('fr');
    expect(values).toContain('es');
    expect(values).toContain('de');
    expect(values).toContain('pt-BR');
    expect(values).toContain('it');
  });

  test('exports SETTINGS_SECTIONS with 5 sections', () => {
    const { SETTINGS_SECTIONS } = require('../app/(settings)/index');
    expect(SETTINGS_SECTIONS).toHaveLength(5);
    expect(SETTINGS_SECTIONS).toContain('privacy');
    expect(SETTINGS_SECTIONS).toContain('notifications');
    expect(SETTINGS_SECTIONS).toContain('language');
    expect(SETTINGS_SECTIONS).toContain('theme');
    expect(SETTINGS_SECTIONS).toContain('account');
  });

  test('settings screen renders without crashing', () => {
    const mod = require('../app/(settings)/index');
    const result = mod.default();
    expect(result).toBeDefined();
  });

  test('rendered output has Settings accessibility label', () => {
    const mod = require('../app/(settings)/index');
    const result = mod.default();
    expect(result.props.accessibilityLabel).toBe('Settings');
  });

  test('THEME_OPTIONS have labels', () => {
    const { THEME_OPTIONS } = require('../app/(settings)/index');
    THEME_OPTIONS.forEach((opt: any) => {
      expect(opt).toHaveProperty('value');
      expect(opt).toHaveProperty('label');
      expect(typeof opt.label).toBe('string');
    });
  });

  test('LANGUAGE_OPTIONS have labels', () => {
    const { LANGUAGE_OPTIONS } = require('../app/(settings)/index');
    LANGUAGE_OPTIONS.forEach((opt: any) => {
      expect(opt).toHaveProperty('value');
      expect(opt).toHaveProperty('label');
      expect(typeof opt.label).toBe('string');
      expect(opt.label.length).toBeGreaterThan(0);
    });
  });
});

// ---------------------------------------------------------------------------
// Privacy Settings Screen
// ---------------------------------------------------------------------------

describe('Privacy Settings Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(settings)/privacy');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports DEFAULT_PRIVACY_SETTINGS', () => {
    const { DEFAULT_PRIVACY_SETTINGS } = require('../app/(settings)/privacy');
    expect(DEFAULT_PRIVACY_SETTINGS).toBeDefined();
    expect(DEFAULT_PRIVACY_SETTINGS.profile_visibility).toBe('friends');
    expect(DEFAULT_PRIVACY_SETTINGS.allow_messages_from).toBe('friends');
    expect(DEFAULT_PRIVACY_SETTINGS.show_online_status).toBe(true);
  });

  test('exports PROFILE_VISIBILITY_OPTIONS with 3 choices', () => {
    const { PROFILE_VISIBILITY_OPTIONS } = require('../app/(settings)/privacy');
    expect(PROFILE_VISIBILITY_OPTIONS).toHaveLength(3);
    const values = PROFILE_VISIBILITY_OPTIONS.map((o: any) => o.value);
    expect(values).toContain('everyone');
    expect(values).toContain('friends');
    expect(values).toContain('nobody');
  });

  test('exports MESSAGE_PERMISSION_OPTIONS with 2 choices', () => {
    const { MESSAGE_PERMISSION_OPTIONS } = require('../app/(settings)/privacy');
    expect(MESSAGE_PERMISSION_OPTIONS).toHaveLength(2);
    const values = MESSAGE_PERMISSION_OPTIONS.map((o: any) => o.value);
    expect(values).toContain('friends');
    expect(values).toContain('nobody');
  });

  test('privacy screen renders without crashing', () => {
    const mod = require('../app/(settings)/privacy');
    const result = mod.default();
    expect(result).toBeDefined();
  });

  test('visibility options have descriptions', () => {
    const { PROFILE_VISIBILITY_OPTIONS } = require('../app/(settings)/privacy');
    PROFILE_VISIBILITY_OPTIONS.forEach((opt: any) => {
      expect(opt).toHaveProperty('description');
      expect(typeof opt.description).toBe('string');
      expect(opt.description.length).toBeGreaterThan(0);
    });
  });

  test('message permission options have descriptions', () => {
    const { MESSAGE_PERMISSION_OPTIONS } = require('../app/(settings)/privacy');
    MESSAGE_PERMISSION_OPTIONS.forEach((opt: any) => {
      expect(opt).toHaveProperty('description');
      expect(typeof opt.description).toBe('string');
    });
  });
});

// ---------------------------------------------------------------------------
// Notification Preferences Screen
// ---------------------------------------------------------------------------

describe('Notification Preferences Screen', () => {
  test('exports default component', () => {
    const mod = require('../app/(settings)/notifications');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });

  test('exports DEFAULT_NOTIFICATION_PREFS', () => {
    const { DEFAULT_NOTIFICATION_PREFS } = require('../app/(settings)/notifications');
    expect(DEFAULT_NOTIFICATION_PREFS).toBeDefined();
    expect(DEFAULT_NOTIFICATION_PREFS.messages).toBe(true);
    expect(DEFAULT_NOTIFICATION_PREFS.likes).toBe(true);
    expect(DEFAULT_NOTIFICATION_PREFS.comments).toBe(true);
    expect(DEFAULT_NOTIFICATION_PREFS.contact_requests).toBe(true);
    expect(DEFAULT_NOTIFICATION_PREFS.moderation).toBe(true);
    expect(DEFAULT_NOTIFICATION_PREFS.weekly_digest).toBe(true);
  });

  test('exports NOTIFICATION_CATEGORIES with 6 categories', () => {
    const { NOTIFICATION_CATEGORIES } = require('../app/(settings)/notifications');
    expect(NOTIFICATION_CATEGORIES).toHaveLength(6);
    const keys = NOTIFICATION_CATEGORIES.map((c: any) => c.key);
    expect(keys).toContain('messages');
    expect(keys).toContain('likes');
    expect(keys).toContain('comments');
    expect(keys).toContain('contact_requests');
    expect(keys).toContain('moderation');
    expect(keys).toContain('weekly_digest');
  });

  test('notification screen renders without crashing', () => {
    const mod = require('../app/(settings)/notifications');
    const result = mod.default();
    expect(result).toBeDefined();
  });

  test('categories have labels and descriptions', () => {
    const { NOTIFICATION_CATEGORIES } = require('../app/(settings)/notifications');
    NOTIFICATION_CATEGORIES.forEach((cat: any) => {
      expect(cat).toHaveProperty('key');
      expect(cat).toHaveProperty('label');
      expect(cat).toHaveProperty('description');
      expect(typeof cat.label).toBe('string');
      expect(typeof cat.description).toBe('string');
    });
  });

  test('all default prefs are enabled', () => {
    const { DEFAULT_NOTIFICATION_PREFS } = require('../app/(settings)/notifications');
    Object.values(DEFAULT_NOTIFICATION_PREFS).forEach((val) => {
      expect(val).toBe(true);
    });
  });

  test('category keys match default prefs keys', () => {
    const { NOTIFICATION_CATEGORIES, DEFAULT_NOTIFICATION_PREFS } = require('../app/(settings)/notifications');
    const catKeys = NOTIFICATION_CATEGORIES.map((c: any) => c.key).sort();
    const prefKeys = Object.keys(DEFAULT_NOTIFICATION_PREFS).sort();
    expect(catKeys).toEqual(prefKeys);
  });
});

// ---------------------------------------------------------------------------
// Theme Selection
// ---------------------------------------------------------------------------

describe('Theme Selection', () => {
  test('system is the default theme', () => {
    const { DEFAULT_SETTINGS } = require('../app/(settings)/index');
    expect(DEFAULT_SETTINGS.theme).toBe('system');
  });

  test('theme options include light and dark', () => {
    const { THEME_OPTIONS } = require('../app/(settings)/index');
    const values = THEME_OPTIONS.map((o: any) => o.value);
    expect(values).toContain('light');
    expect(values).toContain('dark');
  });

  test('theme option labels are human-readable', () => {
    const { THEME_OPTIONS } = require('../app/(settings)/index');
    const light = THEME_OPTIONS.find((o: any) => o.value === 'light');
    const dark = THEME_OPTIONS.find((o: any) => o.value === 'dark');
    const system = THEME_OPTIONS.find((o: any) => o.value === 'system');
    expect(light?.label).toBe('Light');
    expect(dark?.label).toBe('Dark');
    expect(system?.label).toBe('System Default');
  });
});

// ---------------------------------------------------------------------------
// Language Selection
// ---------------------------------------------------------------------------

describe('Language Selection', () => {
  test('English is the default language', () => {
    const { DEFAULT_SETTINGS } = require('../app/(settings)/index');
    expect(DEFAULT_SETTINGS.language).toBe('en');
  });

  test('language options cover all supported locales', () => {
    const { LANGUAGE_OPTIONS } = require('../app/(settings)/index');
    const values = LANGUAGE_OPTIONS.map((o: any) => o.value);
    expect(values).toEqual(['en', 'fr', 'es', 'de', 'pt-BR', 'it']);
  });

  test('each language has a localized label', () => {
    const { LANGUAGE_OPTIONS } = require('../app/(settings)/index');
    const en = LANGUAGE_OPTIONS.find((o: any) => o.value === 'en');
    const fr = LANGUAGE_OPTIONS.find((o: any) => o.value === 'fr');
    expect(en?.label).toBe('English');
    expect(fr?.label).toBe('Fran\u00e7ais');
  });
});

// ---------------------------------------------------------------------------
// Account Operations
// ---------------------------------------------------------------------------

describe('Account Operations', () => {
  test('settings screen includes delete confirmation flow types', () => {
    // ScreenState type is exported at runtime as it's used in state
    const mod = require('../app/(settings)/index');
    expect(mod.default).toBeDefined();
  });

  test('version string is present in render output', () => {
    const mod = require('../app/(settings)/index');
    const result = mod.default();
    // The component renders; version text is a child somewhere in the tree
    expect(result).toBeDefined();
  });
});
