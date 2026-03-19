import { loadLocale, t } from '../src';

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
});
