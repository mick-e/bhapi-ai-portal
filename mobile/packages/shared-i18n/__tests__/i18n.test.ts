import { loadLocale, t } from '../src';

const LOCALES = ['en', 'pt-BR', 'es', 'fr', 'de', 'it'] as const;

const EXPECTED_SECTIONS = ['common', 'auth', 'safety', 'social', 'moderation'];

const SAFETY_KEYS = [
  'dashboard', 'alerts', 'activity', 'settings',
  'risk_overview', 'recent_alerts', 'platform_breakdown',
  'no_alerts', 'alert_detail', 'snooze', 'escalate', 'dismiss',
];

const SOCIAL_KEYS = [
  'feed', 'messages', 'profile', 'create_post',
  'followers', 'following', 'like', 'comment', 'share',
  'new_message', 'contacts', 'add_contact', 'pending_approval',
];

const MODERATION_KEYS = [
  'content_review', 'post_approved', 'post_rejected', 'appeal',
];

describe('i18n', () => {
  test('loads English locale', async () => {
    const translations = await loadLocale('en');
    expect(translations.common.loading).toBe('Loading...');
  });

  test('t() resolves nested keys', async () => {
    const translations = await loadLocale('en');
    expect(t(translations, 'common.loading')).toBe('Loading...');
    expect(t(translations, 'auth.login')).toBe('Log in');
  });

  test('t() returns key for missing translations', async () => {
    const translations = await loadLocale('en');
    expect(t(translations, 'nonexistent.key')).toBe('nonexistent.key');
  });

  test('loads Portuguese locale', async () => {
    const translations = await loadLocale('pt-BR');
    expect(translations.common.loading).toBe('Carregando...');
  });

  test('loads Spanish locale', async () => {
    const translations = await loadLocale('es');
    expect(translations.common.loading).toBe('Cargando...');
  });

  test('loads French locale', async () => {
    const translations = await loadLocale('fr');
    expect(translations.common.loading).toBe('Chargement...');
  });

  test('loads German locale', async () => {
    const translations = await loadLocale('de');
    expect(translations.common.loading).toBe('Wird geladen...');
  });

  test('loads Italian locale', async () => {
    const translations = await loadLocale('it');
    expect(translations.common.loading).toBe('Caricamento...');
  });

  describe.each(LOCALES)('locale %s', (locale) => {
    test('has all required sections', async () => {
      const translations = await loadLocale(locale);
      for (const section of EXPECTED_SECTIONS) {
        expect(translations).toHaveProperty(section);
      }
    });

    test('has all safety keys', async () => {
      const translations = await loadLocale(locale);
      for (const key of SAFETY_KEYS) {
        const value = t(translations, `safety.${key}`);
        expect(value).not.toBe(`safety.${key}`);
        expect(value.length).toBeGreaterThan(0);
      }
    });

    test('has all social keys', async () => {
      const translations = await loadLocale(locale);
      for (const key of SOCIAL_KEYS) {
        const value = t(translations, `social.${key}`);
        expect(value).not.toBe(`social.${key}`);
        expect(value.length).toBeGreaterThan(0);
      }
    });

    test('has all moderation keys', async () => {
      const translations = await loadLocale(locale);
      for (const key of MODERATION_KEYS) {
        const value = t(translations, `moderation.${key}`);
        expect(value).not.toBe(`moderation.${key}`);
        expect(value.length).toBeGreaterThan(0);
      }
    });
  });

  test('English safety strings are correct', async () => {
    const en = await loadLocale('en');
    expect(t(en, 'safety.risk_overview')).toBe('Risk Overview');
    expect(t(en, 'safety.recent_alerts')).toBe('Recent Alerts');
    expect(t(en, 'safety.snooze')).toBe('Snooze');
    expect(t(en, 'safety.escalate')).toBe('Escalate');
    expect(t(en, 'safety.dismiss')).toBe('Dismiss');
  });

  test('English social strings are correct', async () => {
    const en = await loadLocale('en');
    expect(t(en, 'social.followers')).toBe('Followers');
    expect(t(en, 'social.following')).toBe('Following');
    expect(t(en, 'social.new_message')).toBe('New Message');
    expect(t(en, 'social.pending_approval')).toBe('Pending Approval');
  });

  test('English moderation strings are correct', async () => {
    const en = await loadLocale('en');
    expect(t(en, 'moderation.content_review')).toBe('Content Under Review');
    expect(t(en, 'moderation.post_approved')).toBe('Post Approved');
    expect(t(en, 'moderation.post_rejected')).toBe('Post Not Approved');
    expect(t(en, 'moderation.appeal')).toBe('Appeal Decision');
  });

  test('non-English locales have different translations', async () => {
    const en = await loadLocale('en');
    const fr = await loadLocale('fr');
    expect(t(fr, 'safety.risk_overview')).not.toBe(t(en, 'safety.risk_overview'));
    expect(t(fr, 'social.followers')).not.toBe(t(en, 'social.followers'));
    expect(t(fr, 'moderation.content_review')).not.toBe(t(en, 'moderation.content_review'));
  });

  test('fallback to English for unknown locale', async () => {
    const translations = await loadLocale('xx' as any);
    expect(translations.common.loading).toBe('Loading...');
  });
});
