"use client";

import { useState } from "react";
import {
  Settings,
  User,
  Bell,
  Shield,
  CreditCard,
  Globe,
  Key,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/use-auth";

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
        <nav className="w-full lg:w-56 flex-shrink-0">
          <ul className="flex gap-1 overflow-x-auto lg:flex-col">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <li key={tab.value}>
                  <button
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
            <Card title="Profile" description="Update your personal information">
              <div className="max-w-lg space-y-4">
                <Input
                  label="Display name"
                  defaultValue={user?.display_name || ""}
                  placeholder="Your name"
                />
                <Input
                  label="Email address"
                  type="email"
                  defaultValue={user?.email || ""}
                  placeholder="you@example.com"
                />
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">
                    Account type
                  </label>
                  <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600">
                    <Globe className="h-4 w-4" />
                    <span className="capitalize">
                      {user?.account_type || "Family"}
                    </span>
                  </div>
                </div>
                <div className="pt-2">
                  <Button>Save Changes</Button>
                </div>
              </div>
            </Card>
          )}

          {activeTab === "notifications" && (
            <Card
              title="Notifications"
              description="Choose what alerts you receive"
            >
              <div className="max-w-lg space-y-6">
                <NotificationToggle
                  label="Critical safety alerts"
                  description="Immediate notification for blocked or dangerous content"
                  defaultChecked
                  disabled
                />
                <NotificationToggle
                  label="Risk warnings"
                  description="Alerts for medium and high-risk interactions"
                  defaultChecked
                />
                <NotificationToggle
                  label="Spend alerts"
                  description="Budget thresholds and overspend notifications"
                  defaultChecked
                />
                <NotificationToggle
                  label="Member updates"
                  description="New member joins, role changes, invitation status"
                  defaultChecked
                />
                <NotificationToggle
                  label="Weekly digest"
                  description="Summary email of AI activity and safety status"
                  defaultChecked
                />
                <NotificationToggle
                  label="Report notifications"
                  description="Alert when new reports are generated"
                />
                <div className="pt-2">
                  <Button>Save Preferences</Button>
                </div>
              </div>
            </Card>
          )}

          {activeTab === "safety" && (
            <Card
              title="Safety Rules"
              description="Configure content filtering and safety policies"
            >
              <div className="max-w-lg space-y-6">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">
                    Default safety level
                  </label>
                  <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20">
                    <option value="strict">Strict (recommended for children)</option>
                    <option value="moderate">Moderate</option>
                    <option value="permissive">Permissive</option>
                  </select>
                </div>
                <NotificationToggle
                  label="Auto-block critical content"
                  description="Automatically block interactions flagged as critical risk"
                  defaultChecked
                  disabled
                />
                <NotificationToggle
                  label="Prompt logging"
                  description="Store full prompts and responses for review"
                  defaultChecked
                />
                <NotificationToggle
                  label="PII detection"
                  description="Flag interactions containing personal information"
                  defaultChecked
                />
                <div className="pt-2">
                  <Button>Save Rules</Button>
                </div>
              </div>
            </Card>
          )}

          {activeTab === "billing" && (
            <Card
              title="Billing"
              description="Manage your subscription and payment methods"
            >
              <div className="max-w-lg space-y-6">
                <div className="rounded-lg bg-primary-50 p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold text-primary-900">
                        Free Plan
                      </p>
                      <p className="mt-0.5 text-xs text-primary-700">
                        Up to 5 members, basic safety features
                      </p>
                    </div>
                    <Button size="sm">Upgrade</Button>
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-700">
                    Monthly budget
                  </h4>
                  <Input
                    type="number"
                    defaultValue="150"
                    placeholder="Monthly budget in USD"
                    helperText="Set to 0 for unlimited"
                  />
                </div>
                <div className="pt-2">
                  <Button>Update Billing</Button>
                </div>
              </div>
            </Card>
          )}

          {activeTab === "api-keys" && (
            <Card
              title="API Keys"
              description="Manage API keys for the Bhapi proxy"
            >
              <div className="max-w-lg space-y-4">
                <div className="rounded-lg border border-gray-200 p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        Production Key
                      </p>
                      <p className="mt-0.5 font-mono text-xs text-gray-400">
                        bhapi_sk_****...****3f2a
                      </p>
                    </div>
                    <Button variant="ghost" size="sm">
                      Revoke
                    </Button>
                  </div>
                </div>
                <Button variant="secondary">
                  <Key className="h-4 w-4" />
                  Generate New Key
                </Button>
                <p className="text-xs text-gray-400">
                  API keys provide access to the Bhapi proxy. Keep them secure
                  and never share them publicly.
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function NotificationToggle({
  label,
  description,
  defaultChecked = false,
  disabled = false,
}: {
  label: string;
  description: string;
  defaultChecked?: boolean;
  disabled?: boolean;
}) {
  const [checked, setChecked] = useState(defaultChecked);

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
        disabled={disabled}
        onClick={() => !disabled && setChecked(!checked)}
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
