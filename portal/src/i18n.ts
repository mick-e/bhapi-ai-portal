export const locales = ['en', 'fr', 'es', 'de', 'pt', 'it'] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = 'en';

export const localeLabels: Record<Locale, string> = {
  en: 'English',
  fr: 'Français',
  es: 'Español',
  de: 'Deutsch',
  pt: 'Português',
  it: 'Italiano',
};

export function getLocale(): Locale {
  if (typeof window === 'undefined') return defaultLocale;
  const stored = localStorage.getItem('bhapi_locale');
  if (stored && locales.includes(stored as Locale)) return stored as Locale;
  const browserLang = navigator.language.split('-')[0];
  if (locales.includes(browserLang as Locale)) return browserLang as Locale;
  return defaultLocale;
}

export function setLocale(locale: Locale) {
  localStorage.setItem('bhapi_locale', locale);
}
