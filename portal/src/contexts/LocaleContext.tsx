"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import {
  type Locale,
  defaultLocale,
  getLocale,
  setLocale as persistLocale,
} from "@/i18n";

type Messages = Record<string, Record<string, string>>;

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  messages: Messages;
  isLoading: boolean;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

/**
 * Retrieves a nested value from the messages object using a dot-separated key.
 * Example: get(messages, "nav.dashboard") => messages.nav.dashboard
 */
function get(obj: Record<string, unknown>, path: string): string | undefined {
  const parts = path.split(".");
  let current: unknown = obj;
  for (const part of parts) {
    if (current === null || current === undefined || typeof current !== "object") {
      return undefined;
    }
    current = (current as Record<string, unknown>)[part];
  }
  return typeof current === "string" ? current : undefined;
}

async function loadMessages(locale: Locale): Promise<Messages> {
  switch (locale) {
    case "en":
      return (await import("../../messages/en.json")).default;
    case "fr":
      return (await import("../../messages/fr.json")).default;
    case "es":
      return (await import("../../messages/es.json")).default;
    case "de":
      return (await import("../../messages/de.json")).default;
    case "pt":
      return (await import("../../messages/pt.json")).default;
    case "it":
      return (await import("../../messages/it.json")).default;
    case "nl":
      return (await import("../../messages/nl.json")).default;
    case "pl":
      return (await import("../../messages/pl.json")).default;
    case "sv":
      return (await import("../../messages/sv.json")).default;
    default:
      return (await import("../../messages/en.json")).default;
  }
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(defaultLocale);
  const [messages, setMessages] = useState<Messages>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const detected = getLocale();
    setLocaleState(detected);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    loadMessages(locale).then((msgs) => {
      if (!cancelled) {
        setMessages(msgs);
        setIsLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [locale]);

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    persistLocale(newLocale);
  }, []);

  return (
    <LocaleContext.Provider value={{ locale, setLocale, messages, isLoading }}>
      {children}
    </LocaleContext.Provider>
  );
}

/**
 * Hook to access locale context.
 * Returns locale, setLocale, messages, and isLoading.
 */
export function useLocale() {
  const ctx = useContext(LocaleContext);
  if (!ctx) {
    throw new Error("useLocale must be used within a LocaleProvider");
  }
  return ctx;
}

/**
 * Hook that returns a translation function `t(key)` for the given namespace.
 *
 * Usage:
 *   const t = useTranslations("dashboard");
 *   t("title") => looks up messages.dashboard.title
 *
 *   const t = useTranslations();
 *   t("common.loading") => looks up messages.common.loading
 */
export function useTranslations(namespace?: string) {
  const { messages } = useLocale();

  const t = useCallback(
    (key: string): string => {
      const fullKey = namespace ? `${namespace}.${key}` : key;
      return get(messages, fullKey) ?? fullKey;
    },
    [messages, namespace]
  );

  return t;
}
