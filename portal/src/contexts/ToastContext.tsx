"use client";

import { createContext, useCallback, useContext, useState } from "react";

export type ToastSeverity = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  message: string;
  severity: ToastSeverity;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (message: string, severity?: ToastSeverity) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const MAX_TOASTS = 3;
const DURATIONS: Record<ToastSeverity, number> = {
  success: 3000,
  info: 3000,
  warning: 5000,
  error: 5000,
};

let toastCounter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (message: string, severity: ToastSeverity = "success") => {
      const id = `toast-${++toastCounter}`;
      setToasts((prev) => [...prev.slice(-(MAX_TOASTS - 1)), { id, message, severity }]);
      setTimeout(() => removeToast(id), DURATIONS[severity]);
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
