"use client";

import { useState, useEffect, Suspense } from "react";
import {
  Globe,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Mail,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { locales, localeLabels } from "@/i18n";
import { useLocale } from "@/contexts/LocaleContext";
import { useAuth } from "@/hooks/use-auth";
import {
  useGroupSettings,
  useUpdateGroupSettings,
  useUpdateProfile,
} from "@/hooks/use-settings";
import { useToast } from "@/contexts/ToastContext";
import type { NotificationPreferences } from "@/types";

export default function SettingsPage() {
  return (
    <Suspense>
      <SettingsPageInner />
    </Suspense>
  );
}

function SettingsPageInner() {
  const { user } = useAuth();

  const {
    data: settings,
    isLoading,
    isError,
    error,
    refetch,
  } = useGroupSettings();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading settings...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">Failed to load settings</p>
        <p className="mt-1 text-sm text-gray-500">
          {(error as Error)?.message || "Something went wrong"}
        </p>
        <Button variant="secondary" size="sm" className="mt-4" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your profile and notification preferences
        </p>
      </div>

      <ProfileSection
        displayName={user?.display_name || ""}
        email={user?.email || ""}
        accountType={user?.account_type || "family"}
      />

      {settings && (
        <NotificationsSection notifications={settings.notifications} />
      )}
    </div>
  );
}

// ─── Profile Section ─────────────────────────────────────────────────────────

function ProfileSection({
  displayName,
  email,
  accountType,
}: {
  displayName: string;
  email: string;
  accountType: string;
}) {
  const [name, setName] = useState(displayName);
  const [emailVal, setEmailVal] = useState(email);
  const updateProfile = useUpdateProfile();
  const { addToast } = useToast();
  const { locale, setLocale } = useLocale();

  useEffect(() => {
    setName(displayName);
    setEmailVal(email);
  }, [displayName, email]);

  function handleSave() {
    updateProfile.mutate(
      { display_name: name, email: emailVal },
      {
        onSuccess: () => addToast("Profile updated successfully", "success"),
        onError: (err) =>
          addToast((err as Error).message || "Failed to update profile", "error"),
      }
    );
  }

  return (
    <Card title="Profile" description="Update your personal information">
      <div className="max-w-lg space-y-4">
        {updateProfile.isError && (
          <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {(updateProfile.error as Error)?.message || "Failed to update profile"}
          </div>
        )}
        <Input
          label="Display name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Your name"
        />
        <Input
          label="Email address"
          type="email"
          value={emailVal}
          onChange={(e) => setEmailVal(e.target.value)}
          placeholder="you@example.com"
        />
        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-700">
            Account type
          </label>
          <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600">
            <Globe className="h-4 w-4" />
            <span className="capitalize">{accountType}</span>
          </div>
        </div>
        <div>
          <label htmlFor="locale-select" className="mb-1.5 block text-sm font-medium text-gray-700">
            Language
          </label>
          <select
            id="locale-select"
            value={locale}
            onChange={(e) => setLocale(e.target.value as typeof locales[number])}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            {locales.map((l) => (
              <option key={l} value={l}>
                {localeLabels[l]}
              </option>
            ))}
          </select>
          <p className="mt-1.5 text-sm text-gray-500">
            Language changes apply immediately across the app.
          </p>
        </div>
        <div className="pt-2">
          <Button
            onClick={handleSave}
            isLoading={updateProfile.isPending}
            disabled={name === displayName && emailVal === email}
          >
            Save Changes
          </Button>
        </div>
      </div>
    </Card>
  );
}

// ─── Notifications Section ───────────────────────────────────────────────────

function NotificationsSection({
  notifications,
}: {
  notifications: NotificationPreferences;
}) {
  const [prefs, setPrefs] = useState<NotificationPreferences>(notifications);
  const [smsEnabled, setSmsEnabled] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState("");
  const [digestFrequency, setDigestFrequency] = useState("daily");
  const updateSettings = useUpdateGroupSettings();
  const updateProfile = useUpdateProfile();
  const { addToast } = useToast();

  useEffect(() => {
    setPrefs(notifications);
  }, [notifications]);

  function toggle(key: keyof NotificationPreferences) {
    setPrefs((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function handleSave() {
    updateSettings.mutate(
      { notifications: prefs, sms_enabled: smsEnabled, digest_mode: digestFrequency },
      {
        onSuccess: () => addToast("Notification preferences saved", "success"),
        onError: (err) =>
          addToast((err as Error).message || "Failed to save preferences", "error"),
      }
    );
    if (phoneNumber) {
      updateProfile.mutate({ phone_number: phoneNumber });
    }
  }

  return (
    <Card title="Notifications" description="Choose what alerts you receive">
      <div className="max-w-lg space-y-6">
        {/* Digest Frequency Selector */}
        <div>
          <label htmlFor="digest-frequency" className="mb-1.5 block text-sm font-medium text-gray-700">
            Digest frequency
          </label>
          <select
            id="digest-frequency"
            value={digestFrequency}
            onChange={(e) => setDigestFrequency(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="immediate">Immediate (real-time alerts)</option>
            <option value="hourly">Hourly digest</option>
            <option value="daily">Daily digest</option>
            <option value="weekly">Weekly digest</option>
          </select>
          <p className="mt-1.5 text-xs text-gray-500">
            Choose how often you receive batched alert summaries by email.
          </p>
        </div>

        <NotificationToggle
          label="Critical safety alerts"
          description="Immediate notification for blocked or dangerous content"
          checked={prefs.critical_safety}
          disabled
          onToggle={() => {}}
        />
        <NotificationToggle
          label="Risk warnings"
          description="Alerts for medium and high-risk interactions"
          checked={prefs.risk_warnings}
          onToggle={() => toggle("risk_warnings")}
        />
        <NotificationToggle
          label="Spend alerts"
          description="Budget thresholds and overspend notifications"
          checked={prefs.spend_alerts}
          onToggle={() => toggle("spend_alerts")}
        />
        <NotificationToggle
          label="Member updates"
          description="New member joins, role changes, invitation status"
          checked={prefs.member_updates}
          onToggle={() => toggle("member_updates")}
        />
        <NotificationToggle
          label="Weekly digest"
          description="Summary email of AI activity and safety status"
          checked={prefs.weekly_digest}
          onToggle={() => toggle("weekly_digest")}
        />
        <NotificationToggle
          label="Report notifications"
          description="Alert when new reports are generated"
          checked={prefs.report_notifications}
          onToggle={() => toggle("report_notifications")}
        />

        <div className="border-t border-gray-200 pt-6">
          <h4 className="mb-4 text-sm font-semibold text-gray-900">SMS Notifications</h4>
          <NotificationToggle
            label="Enable SMS alerts"
            description="Receive critical alerts via text message (standard rates may apply)"
            checked={smsEnabled}
            onToggle={() => setSmsEnabled(!smsEnabled)}
          />
          {smsEnabled && (
            <div className="mt-4">
              <Input
                label="Phone number"
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="+1 (555) 123-4567"
                helperText="Include country code. Used for SMS alerts only."
              />
            </div>
          )}
        </div>

        <div className="pt-2">
          <Button onClick={handleSave} isLoading={updateSettings.isPending}>
            Save Preferences
          </Button>
        </div>
      </div>
    </Card>
  );
}

// ─── Shared Toggle Component ─────────────────────────────────────────────────

function NotificationToggle({
  label,
  description,
  checked,
  disabled = false,
  onToggle,
}: {
  label: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-gray-900">{label}</p>
        <p className="mt-0.5 text-xs text-gray-500">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => !disabled && onToggle()}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
          checked ? "bg-primary" : "bg-gray-200"
        } ${disabled ? "cursor-not-allowed opacity-60" : ""}`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition-transform ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
}
