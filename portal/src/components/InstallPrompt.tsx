"use client";

import { useState, useEffect, useCallback } from "react";
import { Download, X } from "lucide-react";

const DISMISS_KEY = "bhapi-pwa-install-dismissed";

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export default function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Don't show if already dismissed
    if (typeof window === "undefined") return;
    if (localStorage.getItem(DISMISS_KEY)) return;

    // Don't show if already installed (standalone mode)
    if (window.matchMedia("(display-mode: standalone)").matches) return;

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setVisible(true);
    };

    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstall = useCallback(async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") {
      setVisible(false);
    }
    setDeferredPrompt(null);
  }, [deferredPrompt]);

  const handleDismiss = useCallback(() => {
    setVisible(false);
    setDeferredPrompt(null);
    localStorage.setItem(DISMISS_KEY, "1");
  }, []);

  if (!visible) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 mx-auto max-w-lg rounded-xl border border-orange-200 bg-white p-4 shadow-lg sm:left-auto sm:right-4 sm:w-96">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-orange-50">
          <Download className="h-5 w-5 text-primary-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900">
            Install Bhapi
          </p>
          <p className="mt-0.5 text-xs text-gray-500">
            Add to your home screen for quick access to AI safety monitoring.
          </p>
          <div className="mt-3 flex items-center gap-2">
            <button
              onClick={handleInstall}
              className="rounded-lg bg-primary-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-700 transition-colors"
            >
              Install
            </button>
            <button
              onClick={handleDismiss}
              className="rounded-lg px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
            >
              Not now
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
