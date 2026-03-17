"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  User,
  Bell,
  Shield,
  CreditCard,
  Key,
  Globe,
  Loader2,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  Settings,
  Mail,
  Clock,
  Lock,
  Phone,
  Plus,
  Trash2,
  UserPlus,
  Eye,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { locales, localeLabels, getLocale, setLocale } from "@/i18n";
import { useAuth } from "@/hooks/use-auth";
import {
  useGroupSettings,
  useUpdateGroupSettings,
  useUpdateProfile,
  useApiKeys,
  useGenerateApiKey,
  useRevokeApiKey,
} from "@/hooks/use-settings";
import { useCreateCheckout, useBillingPortal, useTrialStatus } from "@/hooks/use-billing";
import { useToast } from "@/contexts/ToastContext";
import type {
  SafetyLevel,
  NotificationPreferences,
  GroupMember,
} from "@/types";

import {
  useEmergencyContacts,
  useAddEmergencyContact,
  useRemoveEmergencyContact,
} from "@/hooks/use-emergency-contacts";
import type { EmergencyContact } from "@/hooks/use-emergency-contacts";
import { useMembers } from "@/hooks/use-members";
import { useVisibility, useSetVisibility, useSelfView, useSetSelfView } from "@/hooks/use-privacy";

type SettingsTab =
  | "profile"
  | "notifications"
  | "safety"
  | "privacy"
  | "billing"
  | "emergency-contacts"
  | "api-keys";

const tabs: { value: SettingsTab; label: string; icon: typeof Settings }[] = [
  { value: "profile", label: "Profile", icon: User },
  { value: "notifications", label: "Notifications", icon: Bell },
  { value: "safety", label: "Safety Rules", icon: Shield },
  { value: "privacy", label: "Privacy", icon: Eye },
  { value: "billing", label: "Billing", icon: CreditCard },
  { value: "emergency-contacts", label: "Emergency Contacts", icon: Phone },
  { value: "api-keys", label: "API Keys", icon: Key },
];

export default function SettingsPage() {
  return (
    <Suspense>
      <SettingsPageInner />
    </Suspense>
  );
}

function SettingsPageInner() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as SettingsTab) || "profile";
  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);

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
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load settings
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {(error as Error)?.message || "Something went wrong"}
        </p>
        <Button
          variant="secondary"
          size="sm"
          className="mt-4"
          onClick={() => refetch()}
        >
          <RefreshCw className="h-4 w-4" />
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your account and group preferences
        </p>
      </div>

      <div className="flex flex-col gap-8 lg:flex-row">
        {/* Sidebar Tabs */}
        <nav aria-label="Settings sections" className="w-full lg:w-56 flex-shrink-0">
          <ul role="tablist" className="flex gap-1 overflow-x-auto lg:flex-col">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <li key={tab.value}>
                  <button
                    role="tab"
                    aria-selected={activeTab === tab.value}
                    onClick={() => setActiveTab(tab.value)}
                    className={`flex w-full items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                      activeTab === tab.value
                        ? "bg-primary-50 text-primary"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    }`}
                  >
                    <Icon className="h-4 w-4 flex-shrink-0" />
                    {tab.label}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Content */}
        <div className="flex-1">
          {activeTab === "profile" && (
            <ProfileTab
              displayName={user?.display_name || ""}
              email={user?.email || ""}
              accountType={user?.account_type || "family"}
            />
          )}

          {activeTab === "notifications" && settings && (
            <NotificationsTab notifications={settings.notifications} />
          )}

          {activeTab === "safety" && settings && (
            <SafetyTab
              safetyLevel={settings.safety_level}
              autoBlockCritical={settings.auto_block_critical}
              promptLogging={settings.prompt_logging}
              piiDetection={settings.pii_detection}
            />
          )}

          {activeTab === "privacy" && <PrivacyTab />}

          {activeTab === "billing" && settings && (
            <BillingTab plan={settings.plan} />
          )}

          {activeTab === "emergency-contacts" && <EmergencyContactsTab />}

          {activeTab === "api-keys" && <ApiKeysTab />}
        </div>
      </div>
    </div>
  );
}

// ─── Profile Tab ────────────────────────────────────────────────────────────

function ProfileTab({
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

  useEffect(() => {
    setName(displayName);
    setEmailVal(email);
  }, [displayName, email]);

  function handleSave() {
    updateProfile.mutate(
      { display_name: name, email: emailVal },
      {
        onSuccess: () => addToast("Profile updated successfully", "success"),
        onError: (err) => addToast((err as Error).message || "Failed to update profile", "error"),
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
            value={getLocale()}
            onChange={(e) => setLocale(e.target.value as typeof locales[number])}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            {locales.map((locale) => (
              <option key={locale} value={locale}>
                {localeLabels[locale]}
              </option>
            ))}
          </select>
          <p className="mt-1.5 text-sm text-gray-500">
            Changing the language will reload the page.
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

// ─── Notifications Tab ──────────────────────────────────────────────────────

function NotificationsTab({
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
        onError: (err) => addToast((err as Error).message || "Failed to save preferences", "error"),
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

// ─── Safety Tab ─────────────────────────────────────────────────────────────

function SafetyTab({
  safetyLevel: initialLevel,
  autoBlockCritical: initialAutoBlock,
  promptLogging: initialPromptLog,
  piiDetection: initialPiiDetect,
}: {
  safetyLevel: SafetyLevel;
  autoBlockCritical: boolean;
  promptLogging: boolean;
  piiDetection: boolean;
}) {
  const [safetyLevel, setSafetyLevel] = useState<SafetyLevel>(initialLevel);
  const [autoBlock, setAutoBlock] = useState(initialAutoBlock);
  const [promptLog, setPromptLog] = useState(initialPromptLog);
  const [piiDetect, setPiiDetect] = useState(initialPiiDetect);
  const updateSettings = useUpdateGroupSettings();
  const { addToast } = useToast();

  useEffect(() => {
    setSafetyLevel(initialLevel);
    setAutoBlock(initialAutoBlock);
    setPromptLog(initialPromptLog);
    setPiiDetect(initialPiiDetect);
  }, [initialLevel, initialAutoBlock, initialPromptLog, initialPiiDetect]);

  function handleSave() {
    updateSettings.mutate(
      {
        safety_level: safetyLevel,
        auto_block_critical: autoBlock,
        prompt_logging: promptLog,
        pii_detection: piiDetect,
      },
      {
        onSuccess: () => addToast("Safety rules updated", "success"),
        onError: (err) => addToast((err as Error).message || "Failed to update safety rules", "error"),
      }
    );
  }

  return (
    <Card
      title="Safety Rules"
      description="Configure content filtering and safety policies"
    >
      <div className="max-w-lg space-y-6">
        <div>
          <label htmlFor="safety-level" className="mb-1.5 block text-sm font-medium text-gray-700">
            Default safety level
          </label>
          <select
            id="safety-level"
            value={safetyLevel}
            onChange={(e) => setSafetyLevel(e.target.value as SafetyLevel)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="strict">
              Strict (recommended for children)
            </option>
            <option value="moderate">Moderate</option>
            <option value="permissive">Permissive</option>
          </select>
        </div>
        <NotificationToggle
          label="Auto-block critical content"
          description="Automatically block interactions flagged as critical risk"
          checked={autoBlock}
          disabled
          onToggle={() => {}}
        />
        <NotificationToggle
          label="Prompt logging"
          description="Store full prompts and responses for review"
          checked={promptLog}
          onToggle={() => setPromptLog(!promptLog)}
        />
        <NotificationToggle
          label="PII detection"
          description="Flag interactions containing personal information"
          checked={piiDetect}
          onToggle={() => setPiiDetect(!piiDetect)}
        />
        <div className="pt-2">
          <Button onClick={handleSave} isLoading={updateSettings.isPending}>
            Save Rules
          </Button>
        </div>
      </div>
    </Card>
  );
}

// ─── Billing Tab ────────────────────────────────────────────────────────────

function BillingTab({ plan }: { plan: string }) {
  const [billingCycle, setBillingCycle] = useState<"monthly" | "annual">("monthly");
  const [showPlans, setShowPlans] = useState(false);
  const checkout = useCreateCheckout();
  const portal = useBillingPortal();
  const { data: trial } = useTrialStatus();

  const isTrial = trial?.is_trial ?? true;
  const isLocked = trial?.is_locked ?? false;
  const daysRemaining = trial?.days_remaining ?? 14;
  const isPaid = trial ? !trial.is_trial && trial.is_active : plan !== "free";

  function handleUpgrade() {
    checkout.mutate({ plan_type: "family", billing_cycle: billingCycle });
  }

  function handleManage() {
    portal.mutate();
  }

  const trialProgress = Math.min(100, ((14 - daysRemaining) / 14) * 100);

  return (
    <Card
      title="Billing"
      description="Manage your subscription and payment methods"
    >
      <div className="max-w-xl space-y-6">
        {checkout.isError && (
          <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {(checkout.error as Error)?.message || "Failed to start checkout"}
          </div>
        )}
        {portal.isError && (
          <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {(portal.error as Error)?.message || "Failed to open billing portal"}
          </div>
        )}

        {/* Locked State */}
        {isLocked && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-5 space-y-3">
            <div className="flex items-start gap-3">
              <Lock className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-base font-semibold text-red-900">
                  Your free trial has expired
                </h4>
                <p className="mt-1 text-sm text-red-700">
                  Subscribe below to continue using Bhapi, or email{" "}
                  <a
                    href="mailto:contactus@bhapi.io"
                    className="font-medium underline"
                  >
                    contactus@bhapi.io
                  </a>{" "}
                  to request an extension.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Active Trial */}
        {isTrial && !isLocked && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-5 space-y-3">
            <div className="flex items-start gap-3">
              <Clock className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <h4 className="text-base font-semibold text-amber-900">
                  Free Trial — {daysRemaining} day{daysRemaining !== 1 ? "s" : ""} remaining
                </h4>
                <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-amber-200">
                  <div
                    className="h-full rounded-full bg-amber-500 transition-all"
                    style={{ width: `${trialProgress}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-amber-700">
                  {14 - daysRemaining} of 14 days used
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Paid Plan Badge */}
        {isPaid && (
          <div className="rounded-lg bg-primary-50 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-primary" />
                <div>
                  <p className="text-sm font-semibold text-primary-900">
                    {trial?.plan
                      ? trial.plan.charAt(0).toUpperCase() + trial.plan.slice(1) + " Plan"
                      : "Active Plan"}
                  </p>
                  <p className="mt-0.5 text-xs text-primary-700">
                    Your subscription is active
                  </p>
                </div>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleManage}
                isLoading={portal.isPending}
              >
                Manage Subscription
              </Button>
            </div>
          </div>
        )}

        {/* Pricing Cards — visible for trial and locked */}
        {!isPaid && (
          <div className="rounded-lg border border-gray-200 bg-white p-5 space-y-5">
            <div>
              <h4 className="text-base font-semibold text-gray-900">
                Subscribe to Bhapi
              </h4>
              <p className="mt-1 text-sm text-gray-500">
                Unlimited members, advanced safety rules, full compliance suite, and priority support.
              </p>
            </div>

            {/* Billing Cycle Toggle */}
            <div className="flex gap-3">
              <button
                onClick={() => setBillingCycle("monthly")}
                className={`flex-1 rounded-lg border p-4 text-center transition-colors ${
                  billingCycle === "monthly"
                    ? "border-primary bg-primary-50 ring-2 ring-primary/20"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <p className={`text-sm font-medium ${
                  billingCycle === "monthly" ? "text-primary" : "text-gray-700"
                }`}>
                  Monthly
                </p>
                <p className="mt-1 text-2xl font-bold text-gray-900">
                  $9.99
                </p>
                <p className="text-xs text-gray-500">per month</p>
              </button>
              <button
                onClick={() => setBillingCycle("annual")}
                className={`flex-1 rounded-lg border p-4 text-center transition-colors relative ${
                  billingCycle === "annual"
                    ? "border-primary bg-primary-50 ring-2 ring-primary/20"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold text-green-700">
                  Save 20%
                </span>
                <p className={`text-sm font-medium ${
                  billingCycle === "annual" ? "text-primary" : "text-gray-700"
                }`}>
                  Annual
                </p>
                <p className="mt-1 text-2xl font-bold text-gray-900">
                  $95.88
                </p>
                <p className="text-xs text-gray-500">per year ($7.99/mo)</p>
              </button>
            </div>

            {/* Checkout Button */}
            <Button
              onClick={handleUpgrade}
              isLoading={checkout.isPending}
              className="w-full"
            >
              <CreditCard className="h-4 w-4" />
              Subscribe Now
            </Button>

            <p className="text-center text-xs text-gray-400">
              Secure payment via Stripe. Cancel anytime.
            </p>
          </div>
        )}

        {/* Manage subscription for paid users */}
        {isPaid && (
          <div className="rounded-lg border border-gray-200 bg-white p-5 space-y-3">
            <h4 className="text-sm font-semibold text-gray-900">
              Subscription Management
            </h4>
            <p className="text-sm text-gray-500">
              Update your payment method, change your billing cycle, download invoices, or cancel your subscription.
            </p>
            <Button
              onClick={handleManage}
              isLoading={portal.isPending}
              variant="ghost"
            >
              Open Billing Portal
            </Button>
          </div>
        )}

        {/* Plan Comparison */}
        <div className="rounded-lg border border-gray-200 bg-white p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-gray-900">
              Compare Plans
            </h4>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowPlans(!showPlans)}
            >
              {showPlans ? "Hide" : "Show"} Details
            </Button>
          </div>
          {showPlans && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {/* Family */}
              <div className={`rounded-lg border p-4 ${plan === "family" ? "border-primary bg-primary-50" : "border-gray-200"}`}>
                <h5 className="text-sm font-bold text-gray-900">Family</h5>
                <p className="mt-1 text-2xl font-bold text-gray-900">
                  {billingCycle === "monthly" ? "$9.99" : "$99.99"}
                </p>
                <p className="text-xs text-gray-500">{billingCycle === "monthly" ? "/month" : "/year"}</p>
                {plan === "family" && (
                  <span className="mt-2 inline-block rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-white">
                    Current Plan
                  </span>
                )}
                <ul className="mt-3 space-y-1.5 text-xs text-gray-600">
                  <li>Up to 5 family members</li>
                  <li>Real-time AI alerts</li>
                  <li>Safety scores</li>
                  <li>Spend tracking & budgets</li>
                  <li>Content blocking</li>
                  <li>PDF & CSV reports</li>
                </ul>
              </div>
              {/* School */}
              <div className={`rounded-lg border p-4 ${plan === "school" ? "border-primary bg-primary-50" : "border-gray-200"}`}>
                <h5 className="text-sm font-bold text-gray-900">School Starter</h5>
                <p className="mt-1 text-2xl font-bold text-gray-900">
                  {billingCycle === "monthly" ? "$2.99" : "$29.99"}
                </p>
                <p className="text-xs text-gray-500">per student/{billingCycle === "monthly" ? "month" : "year"}</p>
                {plan === "school" && (
                  <span className="mt-2 inline-block rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-white">
                    Current Plan
                  </span>
                )}
                <ul className="mt-3 space-y-1.5 text-xs text-gray-600">
                  <li>Everything in Family</li>
                  <li>SIS integration</li>
                  <li>Class-level grouping</li>
                  <li>Safeguarding reports</li>
                  <li>Federated SSO</li>
                  <li>Behaviour analytics</li>
                </ul>
              </div>
              {/* Enterprise */}
              <div className={`rounded-lg border p-4 ${plan === "enterprise" ? "border-primary bg-primary-50" : "border-gray-200"}`}>
                <h5 className="text-sm font-bold text-gray-900">Enterprise</h5>
                <p className="mt-1 text-2xl font-bold text-gray-900">Custom</p>
                <p className="text-xs text-gray-500">contact us</p>
                {plan === "enterprise" && (
                  <span className="mt-2 inline-block rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-white">
                    Current Plan
                  </span>
                )}
                <ul className="mt-3 space-y-1.5 text-xs text-gray-600">
                  <li>Everything in School</li>
                  <li>Unlimited groups</li>
                  <li>Dedicated manager</li>
                  <li>Custom taxonomy</li>
                  <li>API access</li>
                  <li>Priority SLA</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Change Plan Button (for paid users) */}
        {isPaid && (
          <Button
            onClick={handleManage}
            isLoading={portal.isPending}
            variant="secondary"
            className="w-full"
          >
            Change Plan
          </Button>
        )}

        {/* Contact */}
        {!isPaid && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Mail className="h-4 w-4" />
            <span>
              Questions? Email{" "}
              <a href="mailto:contactus@bhapi.io" className="text-primary-700 underline">
                contactus@bhapi.io
              </a>
            </span>
          </div>
        )}
      </div>
    </Card>
  );
}

// ─── API Keys Tab ───────────────────────────────────────────────────────────

function ApiKeysTab() {
  const { data: keys, isLoading, isError } = useApiKeys();
  const generateKey = useGenerateApiKey();
  const revokeKey = useRevokeApiKey();
  const [newKey, setNewKey] = useState<string | null>(null);
  const [keyName, setKeyName] = useState("");
  const [showGenerate, setShowGenerate] = useState(false);
  const [confirmRevoke, setConfirmRevoke] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  function handleGenerate() {
    generateKey.mutate(
      { name: keyName || undefined },
      {
        onSuccess: (data) => {
          setNewKey(data.key);
          setKeyName("");
          setShowGenerate(false);
        },
      }
    );
  }

  function handleRevoke(keyId: string) {
    revokeKey.mutate(keyId, {
      onSuccess: () => setConfirmRevoke(null),
    });
  }

  function handleCopy() {
    if (newKey) {
      navigator.clipboard.writeText(newKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <Card title="API Keys" description="Manage API keys for the Bhapi proxy">
      <div className="max-w-lg space-y-4">
        {generateKey.isError && (
          <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {(generateKey.error as Error)?.message || "Failed to generate key"}
          </div>
        )}

        {newKey && (
          <div className="rounded-lg border border-green-200 bg-green-50 p-4">
            <p className="text-sm font-medium text-green-800">
              API key created — copy it now, it will not be shown again.
            </p>
            <div className="mt-2 flex items-center gap-2">
              <code className="flex-1 break-all rounded bg-white px-2 py-1 font-mono text-xs text-gray-900">
                {newKey}
              </code>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleCopy}
              >
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
            <button
              onClick={() => setNewKey(null)}
              className="mt-2 text-xs text-green-700 underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {isLoading && (
          <div className="flex items-center gap-2 py-4">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm text-gray-500">Loading keys...</span>
          </div>
        )}

        {isError && (
          <p className="text-sm text-red-600">Failed to load API keys.</p>
        )}

        {keys && keys.length > 0 && (
          <div className="space-y-3">
            {keys.map((k) => (
              <div
                key={k.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 p-4"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {k.name || "Unnamed Key"}
                  </p>
                  <p className="mt-0.5 font-mono text-xs text-gray-400">
                    {k.key_prefix}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-400">
                    Created {new Date(k.created_at).toLocaleDateString()}
                    {k.last_used_at &&
                      ` · Last used ${new Date(k.last_used_at).toLocaleDateString()}`}
                  </p>
                </div>
                {confirmRevoke === k.id ? (
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRevoke(k.id)}
                      isLoading={revokeKey.isPending}
                    >
                      Confirm
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setConfirmRevoke(null)}
                    >
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setConfirmRevoke(k.id)}
                  >
                    Revoke
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}

        {keys && keys.length === 0 && !newKey && (
          <p className="text-sm text-gray-500">No API keys yet.</p>
        )}

        {showGenerate ? (
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <Input
                label="Key name (optional)"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                placeholder="e.g. Production"
              />
            </div>
            <Button
              onClick={handleGenerate}
              isLoading={generateKey.isPending}
              size="sm"
            >
              Create
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setShowGenerate(false);
                setKeyName("");
              }}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <Button variant="secondary" onClick={() => setShowGenerate(true)}>
            <Key className="h-4 w-4" />
            Generate New Key
          </Button>
        )}

        <p className="text-xs text-gray-400">
          API keys provide access to the Bhapi proxy. Keep them secure and
          never share them publicly.
        </p>
      </div>
    </Card>
  );
}

// ─── Emergency Contacts Tab ─────────────────────────────────────────────────

function EmergencyContactsTab() {
  const { data: contacts, isLoading, isError } = useEmergencyContacts();
  const addContact = useAddEmergencyContact();
  const removeContact = useRemoveEmergencyContact();
  const { addToast } = useToast();

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [relationship, setRelationship] = useState("trusted_adult");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [notifyOn, setNotifyOn] = useState<string[]>(["critical"]);
  const [consentGiven, setConsentGiven] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  function handleAdd() {
    if (!name || (!phone && !email)) return;
    addContact.mutate(
      {
        name,
        relationship,
        phone: phone || undefined,
        email: email || undefined,
        notify_on: notifyOn,
        consent_given: consentGiven,
      },
      {
        onSuccess: () => {
          setShowForm(false);
          setName("");
          setPhone("");
          setEmail("");
          setNotifyOn(["critical"]);
          setConsentGiven(false);
          addToast("Emergency contact added", "success");
        },
        onError: (err) =>
          addToast((err as Error).message || "Failed to add contact", "error"),
      }
    );
  }

  function handleRemove(id: string) {
    removeContact.mutate(id, {
      onSuccess: () => {
        setConfirmDelete(null);
        addToast("Emergency contact removed", "success");
      },
    });
  }

  function toggleNotifyType(type: string) {
    setNotifyOn((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  }

  const relationshipLabels: Record<string, string> = {
    grandparent: "Grandparent",
    school_counselor: "School Counselor",
    trusted_adult: "Trusted Adult",
    aunt_uncle: "Aunt / Uncle",
    family_friend: "Family Friend",
    therapist: "Therapist",
    other: "Other",
  };

  return (
    <Card
      title="Emergency Contacts"
      description="People who should be notified during critical safety events"
    >
      <div className="max-w-lg space-y-4">
        {addContact.isError && (
          <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {(addContact.error as Error)?.message || "Failed to add contact"}
          </div>
        )}

        {isLoading && (
          <div className="flex items-center gap-2 py-4">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm text-gray-500">Loading contacts...</span>
          </div>
        )}

        {isError && (
          <p className="text-sm text-red-600">Failed to load emergency contacts.</p>
        )}

        {contacts && contacts.length > 0 && (
          <div className="space-y-3">
            {contacts.map((c: EmergencyContact) => (
              <div
                key={c.id}
                className="flex items-start justify-between rounded-lg border border-gray-200 p-4"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{c.name}</p>
                  <p className="mt-0.5 text-xs text-gray-500 capitalize">
                    {relationshipLabels[c.relationship] || c.relationship}
                  </p>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-400">
                    {c.phone && (
                      <span className="flex items-center gap-1">
                        <Phone className="h-3 w-3" /> {c.phone}
                      </span>
                    )}
                    {c.email && (
                      <span className="flex items-center gap-1">
                        <Mail className="h-3 w-3" /> {c.email}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex gap-1">
                    {c.notify_on.map((type) => (
                      <span
                        key={type}
                        className="rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-600"
                      >
                        {type}
                      </span>
                    ))}
                  </div>
                  {!c.consent_given && (
                    <p className="mt-1 text-xs text-amber-600">
                      Consent not yet given
                    </p>
                  )}
                </div>
                {confirmDelete === c.id ? (
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemove(c.id)}
                      isLoading={removeContact.isPending}
                    >
                      Confirm
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setConfirmDelete(null)}
                    >
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setConfirmDelete(c.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}

        {contacts && contacts.length === 0 && !showForm && (
          <p className="text-sm text-gray-500">
            No emergency contacts yet. Add someone who should be notified during
            critical safety events.
          </p>
        )}

        {showForm ? (
          <div className="space-y-3 rounded-lg border border-gray-200 p-4">
            <h4 className="text-sm font-semibold text-gray-900">
              Add Emergency Contact
            </h4>
            <Input
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Full name"
            />
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Relationship
              </label>
              <select
                value={relationship}
                onChange={(e) => setRelationship(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                {Object.entries(relationshipLabels).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <Input
              label="Phone (optional)"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1 (555) 123-4567"
            />
            <Input
              label="Email (optional)"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="contact@example.com"
            />
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Notify on
              </label>
              <div className="flex flex-wrap gap-2">
                {["critical", "self_harm", "csam_adjacent"].map((type) => (
                  <button
                    key={type}
                    onClick={() => toggleNotifyType(type)}
                    className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                      notifyOn.includes(type)
                        ? "border-red-200 bg-red-50 text-red-700"
                        : "border-gray-200 text-gray-500 hover:bg-gray-50"
                    }`}
                  >
                    {type.replace("_", " ")}
                  </button>
                ))}
              </div>
            </div>
            <NotificationToggle
              label="Contact has given consent"
              description="This person has agreed to be contacted during emergencies"
              checked={consentGiven}
              onToggle={() => setConsentGiven(!consentGiven)}
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowForm(false);
                  setName("");
                  setPhone("");
                  setEmail("");
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleAdd}
                isLoading={addContact.isPending}
                disabled={!name || (!phone && !email)}
              >
                Add Contact
              </Button>
            </div>
          </div>
        ) : (
          <Button variant="secondary" onClick={() => setShowForm(true)}>
            <UserPlus className="h-4 w-4" />
            Add Emergency Contact
          </Button>
        )}

        <p className="text-xs text-gray-400">
          Emergency contacts will be notified via SMS and/or email when critical
          safety events are detected. Ensure you have their consent before adding them.
        </p>
      </div>
    </Card>
  );
}

// ─── Privacy Tab ────────────────────────────────────────────────────────────

const SELF_VIEW_SECTIONS = [
  { value: "safety_score", label: "Safety Score" },
  { value: "time_usage", label: "Time Usage" },
  { value: "literacy", label: "Literacy Progress" },
  { value: "rewards", label: "Rewards" },
];

function PrivacyTab() {
  const { data: membersData, isLoading } = useMembers({ page_size: 10 });
  const { addToast } = useToast();
  const setSelfView = useSetSelfView();
  const setVisibility = useSetVisibility();

  const members = membersData?.items ?? [];
  const childMembers = members.filter(
    (m: GroupMember) => m.role === "member" || m.role === "viewer"
  );

  if (isLoading) {
    return (
      <Card title="Privacy" description="Control who sees what">
        <div className="flex items-center gap-2 py-4">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm text-gray-500">Loading members...</span>
        </div>
      </Card>
    );
  }

  if (childMembers.length === 0) {
    return (
      <Card title="Privacy" description="Control who sees what">
        <p className="text-sm text-gray-500">
          No child members in your group yet. Add a member to configure privacy
          settings.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card title="Privacy" description="Control sibling visibility and child dashboard access">
        <div className="max-w-lg space-y-6">
          {childMembers.map((child: GroupMember) => (
            <PrivacyMemberRow
              key={child.id}
              member={child}
              onSetSelfView={(memberId, enabled, sections) => {
                setSelfView.mutate(
                  { memberId, data: { enabled, sections } },
                  {
                    onSuccess: () =>
                      addToast(
                        enabled ? "Self-view enabled" : "Self-view disabled",
                        "success"
                      ),
                    onError: (err) =>
                      addToast(
                        (err as Error).message || "Failed to update",
                        "error"
                      ),
                  }
                );
              }}
            />
          ))}
        </div>
      </Card>

      <Card title="COPPA 2026 Privacy Controls" description="Third-party data sharing, retention, and parental verification">
        <p className="text-sm text-gray-500 mb-3">
          Manage granular consent for third-party data processing, data retention
          policies, push notification consent, and parental identity verification.
        </p>
        <a
          href="/settings/privacy"
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700"
        >
          <Shield className="h-4 w-4" />
          Open COPPA Privacy Controls
        </a>
      </Card>
    </div>
  );
}

function PrivacyMemberRow({
  member,
  onSetSelfView,
}: {
  member: GroupMember;
  onSetSelfView: (memberId: string, enabled: boolean, sections: string[]) => void;
}) {
  const { data: selfView } = useSelfView(member.id);
  const [selfViewEnabled, setSelfViewEnabled] = useState(false);
  const [selectedSections, setSelectedSections] = useState<string[]>([]);

  useEffect(() => {
    if (selfView) {
      setSelfViewEnabled(selfView.enabled);
      setSelectedSections(selfView.sections);
    }
  }, [selfView]);

  function toggleSection(section: string) {
    setSelectedSections((prev) =>
      prev.includes(section)
        ? prev.filter((s) => s !== section)
        : [...prev, section]
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-sm font-bold text-primary">
            {member.display_name.charAt(0).toUpperCase()}
          </div>
          <span className="text-sm font-medium text-gray-900">
            {member.display_name}
          </span>
        </div>
      </div>

      <div className="space-y-2">
        <NotificationToggle
          label="Enable self-view dashboard"
          description="Allow this child to see their own safety data"
          checked={selfViewEnabled}
          onToggle={() => {
            const newVal = !selfViewEnabled;
            setSelfViewEnabled(newVal);
            onSetSelfView(
              member.id,
              newVal,
              newVal ? selectedSections : []
            );
          }}
        />

        {selfViewEnabled && (
          <div className="ml-4 space-y-2 border-l-2 border-gray-100 pl-4">
            <p className="text-xs font-medium text-gray-500">
              Visible sections:
            </p>
            {SELF_VIEW_SECTIONS.map((section) => (
              <label
                key={section.value}
                className="flex items-center gap-2 text-sm text-gray-700"
              >
                <input
                  type="checkbox"
                  checked={selectedSections.includes(section.value)}
                  onChange={() => {
                    toggleSection(section.value);
                    const updated = selectedSections.includes(section.value)
                      ? selectedSections.filter((s) => s !== section.value)
                      : [...selectedSections, section.value];
                    onSetSelfView(member.id, true, updated);
                  }}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                {section.label}
              </label>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Shared Toggle Component ────────────────────────────────────────────────

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
