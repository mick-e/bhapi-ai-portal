"use client";

import { useState, useEffect, useCallback } from "react";
import { Download, X, Bookmark } from "lucide-react";

const DISMISS_KEY = "bhapi-pwa-install-dismissed";
const SHOW_DELAY_MS = 5000; // Wait 5s before showing fallback prompt

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

type PromptMode = "native" | "fallback" | null;

function detectBrowser(): "chrome" | "edge" | "firefox" | "safari" | "other" {
  if (typeof navigator === "undefined") return "other";
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes("edg/")) return "edge";
  if (ua.includes("firefox")) return "firefox";
  if (ua.includes("safari") && !ua.includes("chrome")) return "safari";
  if (ua.includes("chrome")) return "chrome";
  return "other";
}

function getFallbackInstructions(browser: string): string {
  switch (browser) {
    case "firefox":
      return "Bookmark this page or add it to your toolbar for quick access.";
    case "safari":
      return "Tap the Share button, then \"Add to Home Screen\" to install.";
    case "chrome":
      return "Open the browser menu (⋮) and select \"Install Bhapi AI Safety Portal\".";
    default:
      return "Bookmark this page for quick access to AI safety monitoring.";
  }
}

export default function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [mode, setMode] = useState<PromptMode>(null);
  const [browser, setBrowser] = useState<string>("other");

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (localStorage.getItem(DISMISS_KEY)) return;
    if (window.matchMedia("(display-mode: standalone)").matches) return;

    const detectedBrowser = detectBrowser();
    setBrowser(detectedBrowser);

    let fallbackTimer: ReturnType<typeof setTimeout> | null = null;
    let gotNativePrompt = false;

    const handler = (e: Event) => {
      e.preventDefault();
      gotNativePrompt = true;
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setMode("native");
      if (fallbackTimer) clearTimeout(fallbackTimer);
    };

    window.addEventListener("beforeinstallprompt", handler);

    // If beforeinstallprompt doesn't fire after delay, show fallback
    fallbackTimer = setTimeout(() => {
      if (!gotNativePrompt) {
        setMode("fallback");
      }
    }, SHOW_DELAY_MS);

    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
      if (fallbackTimer) clearTimeout(fallbackTimer);
    };
  }, []);

  const handleInstall = useCallback(async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") {
      setMode(null);
    }
    setDeferredPrompt(null);
  }, [deferredPrompt]);

  const handleDismiss = useCallback(() => {
    setMode(null);
    setDeferredPrompt(null);
    localStorage.setItem(DISMISS_KEY, "1");
  }, []);

  if (!mode) return null;

  const isNative = mode === "native" && deferredPrompt;
  const IconComponent = isNative ? Download : Bookmark;

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 mx-auto max-w-lg rounded-xl border border-orange-200 bg-white p-4 shadow-lg sm:left-auto sm:right-4 sm:w-96">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-orange-50">
          <IconComponent className="h-5 w-5 text-primary-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900">
            {isNative ? "Install Bhapi" : "Add Bhapi to your browser"}
          </p>
          <p className="mt-0.5 text-xs text-gray-500">
            {isNative
              ? "Add to your home screen for quick access to AI safety monitoring."
              : getFallbackInstructions(browser)}
          </p>
          <div className="mt-3 flex items-center gap-2">
            {isNative ? (
              <button
                onClick={handleInstall}
                className="rounded-lg bg-primary-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-700 transition-colors"
              >
                Install
              </button>
            ) : null}
            <button
              onClick={handleDismiss}
              className="rounded-lg px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
            >
              {isNative ? "Not now" : "Dismiss"}
            </button>
          </div>
        </div>
        <button
          onClick={handleDismiss}
          className="shrink-0 rounded-md p-1 text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Dismiss install prompt"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
