import en from '../locales/en.json';

type Locale = 'en' | 'pt-BR' | 'es' | 'fr' | 'de' | 'it';

const localeLoaders: Record<Locale, () => Promise<typeof en>> = {
  en: () => Promise.resolve(en),
  'pt-BR': () => import('../locales/pt-BR.json') as Promise<typeof en>,
  es: () => import('../locales/es.json') as Promise<typeof en>,
  fr: () => import('../locales/fr.json') as Promise<typeof en>,
  de: () => import('../locales/de.json') as Promise<typeof en>,
  it: () => import('../locales/it.json') as Promise<typeof en>,
};

export async function loadLocale(locale: Locale): Promise<typeof en> {
  const loader = localeLoaders[locale] ?? localeLoaders.en;
  return loader();
}

export function t(translations: typeof en, key: string): string {
  const parts = key.split('.');
  let current: unknown = translations;
  for (const part of parts) {
    if (current && typeof current === 'object' && part in current) {
      current = (current as Record<string, unknown>)[part];
    } else {
      return key;
    }
  }
  return typeof current === 'string' ? current : key;
}

export type { Locale };
