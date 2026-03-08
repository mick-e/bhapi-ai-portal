"use client";

import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from "lucide-react";
import { useToast, type ToastSeverity } from "@/contexts/ToastContext";

const icons: Record<ToastSeverity, typeof Info> = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const styles: Record<ToastSeverity, string> = {
  success: "bg-green-50 text-green-800 ring-green-200",
  error: "bg-red-50 text-red-800 ring-red-200",
  warning: "bg-amber-50 text-amber-800 ring-amber-200",
  info: "bg-blue-50 text-blue-800 ring-blue-200",
};

const iconStyles: Record<ToastSeverity, string> = {
  success: "text-green-500",
  error: "text-red-500",
  warning: "text-amber-500",
  info: "text-blue-500",
};

export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      aria-label="Notifications"
      className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2"
    >
      {toasts.map((toast) => {
        const Icon = icons[toast.severity];
        return (
          <div
            key={toast.id}
            role="alert"
            className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium shadow-lg ring-1 animate-in slide-in-from-right ${styles[toast.severity]}`}
          >
            <Icon className={`h-4 w-4 flex-shrink-0 ${iconStyles[toast.severity]}`} />
            <span className="flex-1">{toast.message}</span>
            <button
              onClick={() => removeToast(toast.id)}
              className="ml-2 rounded p-0.5 opacity-60 hover:opacity-100 transition-opacity"
              aria-label="Dismiss notification"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
