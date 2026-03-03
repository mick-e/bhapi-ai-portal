"use client";

import { useState, useEffect } from "react";
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
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/use-auth";
import {
  useGroupSettings,
  useUpdateGroupSettings,
  useUpdateProfile,
  useApiKeys,
  useGenerateApiKey,
  useRevokeApiKey,
} from "@/hooks/use-settings";
import { useCreateCheckout } from "@/hooks/use-billing";
import type {
  SafetyLevel,
  NotificationPreferences,
} from "@/types";

type SettingsTab =
  | "profile"
  | "notifications"
  | "safety"
  | "billing"
  | "api-keys";

const tabs: { value: SettingsTab; label: string; icon: typeof Settings }[] = [
  { value: "profile", label: "Profile", icon: User },
  { value: "notifications", label: "Notifications", icon: Bell },
  { value: "safety", label: "Safety Rules", icon: Shield },
  { value: "billing", label: "Billing", icon: CreditCard },
  { value: "api-keys", label: "API Keys", icon: Key },
];

export default function SettingsPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");

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

          {activeTab === "billing" && settings && (
            <BillingTab
              plan={settings.plan}
              monthlyBudget={settings.monthly_budget_usd}
            />
          )}

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
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setName(displayName);
    setEmailVal(email);
  }, [displayName, email]);

  function handleSave() {
    updateProfile.mutate(
      { display_name: name, email: emailVal },
      {
        onSuccess: () => {
          setSaved(true);
          setTimeout(() => setSaved(false), 3000);
        },
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
        {saved && (
          <div className="flex items-center gap-2 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-600">
            <CheckCircle2 className="h-4 w-4" />
            Profile updated successfully
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
  const updateSettings = useUpdateGroupSettings();
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setPrefs(notifications);
  }, [notifications]);

  function toggle(key: keyof NotificationPreferences) {
    setPrefs((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function handleSave() {
    updateSettings.mutate(
      { notifications: prefs },
      {
        onSuccess: () => {
          setSaved(true);
          setTimeout(() => setSaved(false), 3000);
        },
      }
    );
  }

  return (
    <Card title="Notifications" description="Choose what alerts you receive">
      <div className="max-w-lg space-y-6">
        {saved && (
          <div className="flex items-center gap-2 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-600">
            <CheckCircle2 className="h-4 w-4" />
            Notification preferences saved
          </div>
        )}
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
  const [saved, setSaved] = useState(false);

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
        onSuccess: () => {
          setSaved(true);
          setTimeout(() => setSaved(false), 3000);
        },
      }
    );
  }

  return (
    <Card
      title="Safety Rules"
      description="Configure content filtering and safety policies"
    >
      <div className="max-w-lg space-y-6">
        {saved && (
          <div className="flex items-center gap-2 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-600">
            <CheckCircle2 className="h-4 w-4" />
            Safety rules updated
          </div>
        )}
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

function BillingTab({
  plan,
  monthlyBudget,
}: {
  plan: string;
  monthlyBudget: number;
}) {
  const [budget, setBudget] = useState(String(monthlyBudget));
  const updateSettings = useUpdateGroupSettings();
  const [saved, setSaved] = useState(false);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [billingCycle, setBillingCycle] = useState<"monthly" | "annual">("monthly");
  const checkout = useCreateCheckout();

  useEffect(() => {
    setBudget(String(monthlyBudget));
  }, [monthlyBudget]);

  function handleSave() {
    const budgetNum = parseFloat(budget);
    if (isNaN(budgetNum) || budgetNum < 0) return;
    updateSettings.mutate(
      { monthly_budget_usd: budgetNum },
      {
        onSuccess: () => {
          setSaved(true);
          setTimeout(() => setSaved(false), 3000);
        },
      }
    );
  }

  function handleUpgrade() {
    checkout.mutate({ plan_type: "family", billing_cycle: billingCycle });
  }

  const planLabels: Record<string, { name: string; description: string }> = {
    free: { name: "Free Plan", description: "Up to 5 members, basic safety features" },
    starter: { name: "Starter Plan", description: "Up to 15 members, advanced safety" },
    pro: { name: "Pro Plan", description: "Unlimited members, full compliance" },
    enterprise: { name: "Enterprise", description: "Custom limits, dedicated support" },
  };

  const planInfo = planLabels[plan] || planLabels.free;

  return (
    <Card
      title="Billing"
      description="Manage your subscription and payment methods"
    >
      <div className="max-w-lg space-y-6">
        {saved && (
          <div className="flex items-center gap-2 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-600">
            <CheckCircle2 className="h-4 w-4" />
            Billing settings updated
          </div>
        )}

        {checkout.isError && (
          <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {(checkout.error as Error)?.message || "Failed to start checkout"}
          </div>
        )}

        <div className="rounded-lg bg-primary-50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-primary-900">
                {planInfo.name}
              </p>
              <p className="mt-0.5 text-xs text-primary-700">
                {planInfo.description}
              </p>
            </div>
            {plan === "free" && (
              <Button size="sm" onClick={() => setShowUpgrade(true)}>
                Upgrade
              </Button>
            )}
          </div>
        </div>

        {showUpgrade && (
          <div className="rounded-lg border border-primary-200 bg-white p-4 space-y-4">
            <h4 className="text-sm font-semibold text-gray-900">
              Upgrade to Family Plan
            </h4>
            <p className="text-xs text-gray-500">
              Unlimited members, advanced safety rules, full compliance suite.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setBillingCycle("monthly")}
                className={`flex-1 rounded-lg border p-3 text-center text-sm transition-colors ${
                  billingCycle === "monthly"
                    ? "border-primary bg-primary-50 font-medium text-primary"
                    : "border-gray-200 text-gray-600 hover:border-gray-300"
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => setBillingCycle("annual")}
                className={`flex-1 rounded-lg border p-3 text-center text-sm transition-colors ${
                  billingCycle === "annual"
                    ? "border-primary bg-primary-50 font-medium text-primary"
                    : "border-gray-200 text-gray-600 hover:border-gray-300"
                }`}
              >
                Annual
                <span className="ml-1 text-xs text-green-600">(save 20%)</span>
              </button>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={handleUpgrade}
                isLoading={checkout.isPending}
              >
                <CreditCard className="h-4 w-4" />
                Continue to Checkout
              </Button>
              <Button
                variant="ghost"
                onClick={() => setShowUpgrade(false)}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}

        <div>
          <h4 className="text-sm font-medium text-gray-700">
            Monthly budget
          </h4>
          <Input
            type="number"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            placeholder="Monthly budget in USD"
            helperText="Set to 0 for unlimited"
          />
        </div>
        <div className="pt-2">
          <Button
            onClick={handleSave}
            isLoading={updateSettings.isPending}
            disabled={budget === String(monthlyBudget)}
          >
            Update Billing
          </Button>
        </div>
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
