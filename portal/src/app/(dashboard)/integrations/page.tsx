"use client";

import { useState } from "react";
import {
  Plug,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Plus,
  Unplug,
  RotateCw,
  CheckCircle2,
  XCircle,
  Clock,
  Shield,
  Users,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/use-auth";
import {
  useConnections,
  useConnectSIS,
  useSyncConnection,
  useDisconnectSIS,
  useSSOConfigs,
  useUpdateSSOConfig,
  useTriggerDirectorySync,
} from "@/hooks/use-integrations";
import { useToast } from "@/contexts/ToastContext";

const providerOptions = [
  { value: "clever", label: "Clever" },
  { value: "classlink", label: "ClassLink" },
];

const statusStyles: Record<string, { bg: string; text: string }> = {
  connected: { bg: "bg-green-100", text: "text-green-700" },
  syncing: { bg: "bg-blue-100", text: "text-blue-700" },
  error: { bg: "bg-red-100", text: "text-red-700" },
  disconnected: { bg: "bg-gray-100", text: "text-gray-600" },
};

export default function IntegrationsPage() {
  const { user } = useAuth();
  const groupId = user?.group_id || null;
  const { addToast } = useToast();

  const {
    data: connections,
    isLoading,
    isError,
    error,
    refetch,
  } = useConnections(groupId);

  const { data: ssoConfigs } = useSSOConfigs(groupId);
  const updateSSOConfig = useUpdateSSOConfig();
  const triggerDirectorySync = useTriggerDirectorySync();

  const connectSIS = useConnectSIS();
  const syncConnection = useSyncConnection();
  const disconnectSIS = useDisconnectSIS();

  const [showForm, setShowForm] = useState(false);
  const [provider, setProvider] = useState("clever");
  const [accessToken, setAccessToken] = useState("");
  const [confirmDisconnect, setConfirmDisconnect] = useState<string | null>(null);

  function handleToggleAutoProvision(configId: string, currentValue: boolean) {
    if (!groupId) return;
    updateSSOConfig.mutate(
      {
        configId,
        groupId,
        data: { auto_provision_members: !currentValue },
      },
      {
        onSuccess: () =>
          addToast(
            `Auto-provisioning ${!currentValue ? "enabled" : "disabled"}`,
            "success"
          ),
        onError: (err) =>
          addToast((err as Error).message || "Failed to update SSO config", "error"),
      }
    );
  }

  function handleDirectorySync(configId: string) {
    if (!groupId) return;
    triggerDirectorySync.mutate(
      { configId, groupId },
      {
        onSuccess: (data) =>
          addToast(
            `Directory sync complete: ${data.synced} synced, ${data.skipped} skipped`,
            "success"
          ),
        onError: (err) =>
          addToast((err as Error).message || "Directory sync failed", "error"),
      }
    );
  }

  function handleConnect() {
    if (!groupId || !accessToken.trim()) return;
    connectSIS.mutate(
      {
        group_id: groupId,
        provider,
        access_token: accessToken.trim(),
      },
      {
        onSuccess: () => {
          addToast("SIS provider connected", "success");
          setShowForm(false);
          setAccessToken("");
        },
        onError: (err) =>
          addToast((err as Error).message || "Failed to connect", "error"),
      }
    );
  }

  function handleSync(connectionId: string) {
    if (!groupId) return;
    syncConnection.mutate(
      { connectionId, groupId },
      {
        onSuccess: (data) =>
          addToast(
            `Sync complete: ${data.members_created} created, ${data.members_updated} updated`,
            "success"
          ),
        onError: (err) =>
          addToast((err as Error).message || "Sync failed", "error"),
      }
    );
  }

  function handleDisconnect(connectionId: string) {
    if (!groupId) return;
    disconnectSIS.mutate(
      { connectionId, groupId },
      {
        onSuccess: () => {
          addToast("Provider disconnected", "success");
          setConfirmDisconnect(null);
        },
        onError: (err) =>
          addToast((err as Error).message || "Failed to disconnect", "error"),
      }
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading integrations...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load integrations
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
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Integrations</h1>
          <p className="mt-1 text-sm text-gray-500">
            Connect Student Information Systems to sync members automatically
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4" />
          Connect Provider
        </Button>
      </div>

      {/* Connect Form */}
      {showForm && (
        <Card title="Connect SIS Provider" className="mb-6">
          <div className="max-w-lg space-y-4">
            {connectSIS.isError && (
              <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                {(connectSIS.error as Error)?.message || "Failed to connect"}
              </div>
            )}
            <div>
              <label
                htmlFor="sis-provider"
                className="mb-1.5 block text-sm font-medium text-gray-700"
              >
                Provider
              </label>
              <select
                id="sis-provider"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                {providerOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <Input
              label="Access Token"
              type="password"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              placeholder="Paste your SIS access token"
              helperText="You can find this in your SIS provider's admin dashboard."
            />
            <div className="flex gap-2 pt-2">
              <Button
                onClick={handleConnect}
                isLoading={connectSIS.isPending}
                disabled={!accessToken.trim()}
              >
                Connect
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setShowForm(false);
                  setAccessToken("");
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Connections List */}
      <div className="space-y-4">
        {(!connections || connections.length === 0) && (
          <Card>
            <div className="py-12 text-center">
              <Plug className="mx-auto h-12 w-12 text-gray-300" />
              <p className="mt-4 text-sm text-gray-500">
                No SIS providers connected
              </p>
              <p className="mt-1 text-xs text-gray-400">
                Connect Clever or ClassLink to import members automatically
              </p>
            </div>
          </Card>
        )}

        {connections?.map((conn) => {
          const style = statusStyles[conn.status] || statusStyles.disconnected;
          return (
            <Card key={conn.id}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
                    <Plug className="h-5 w-5 text-primary-600" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900 capitalize">
                      {conn.provider}
                    </p>
                    <div className="mt-0.5 flex items-center gap-3 text-xs text-gray-500">
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${style.bg} ${style.text}`}
                      >
                        {conn.status === "connected" && (
                          <CheckCircle2 className="h-3 w-3" />
                        )}
                        {conn.status === "error" && (
                          <XCircle className="h-3 w-3" />
                        )}
                        {conn.status}
                      </span>
                      {conn.last_synced && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          Last synced{" "}
                          {new Date(conn.last_synced).toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleSync(conn.id)}
                    isLoading={
                      syncConnection.isPending &&
                      syncConnection.variables?.connectionId === conn.id
                    }
                    aria-label={`Sync ${conn.provider}`}
                  >
                    <RotateCw className="h-4 w-4" />
                    Sync
                  </Button>
                  {confirmDisconnect === conn.id ? (
                    <div className="flex gap-1">
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDisconnect(conn.id)}
                        isLoading={disconnectSIS.isPending}
                      >
                        Confirm
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setConfirmDisconnect(null)}
                      >
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setConfirmDisconnect(conn.id)}
                      aria-label={`Disconnect ${conn.provider}`}
                    >
                      <Unplug className="h-4 w-4" />
                      Disconnect
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* SSO Configuration */}
      <div className="mt-10">
        <div className="mb-4">
          <h2 className="text-lg font-bold text-gray-900">
            Single Sign-On (SSO)
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Manage SSO configurations and automatic member provisioning
          </p>
        </div>

        {(!ssoConfigs || ssoConfigs.length === 0) ? (
          <Card>
            <div className="py-12 text-center">
              <Shield className="mx-auto h-12 w-12 text-gray-300" />
              <p className="mt-4 text-sm text-gray-500">
                No SSO providers configured
              </p>
              <p className="mt-1 text-xs text-gray-400">
                Set up Google Workspace or Microsoft Entra SSO to enable
                automatic member provisioning
              </p>
            </div>
          </Card>
        ) : (
          <div className="space-y-4">
            {ssoConfigs.map((config) => {
              const providerLabel =
                config.provider === "google_workspace"
                  ? "Google Workspace"
                  : "Microsoft Entra";
              return (
                <Card key={config.id}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-50">
                        <Shield className="h-5 w-5 text-teal-600" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-900">
                          {providerLabel}
                        </p>
                        <div className="mt-0.5 flex items-center gap-3 text-xs text-gray-500">
                          {config.tenant_id && (
                            <span>Domain: {config.tenant_id}</span>
                          )}
                          <span className="flex items-center gap-1">
                            <Users className="h-3 w-3" />
                            Auto-provision:{" "}
                            {config.auto_provision_members ? "On" : "Off"}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        role="switch"
                        aria-checked={config.auto_provision_members}
                        aria-label={`Toggle auto-provisioning for ${providerLabel}`}
                        onClick={() =>
                          handleToggleAutoProvision(
                            config.id,
                            config.auto_provision_members
                          )
                        }
                        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary/20 ${
                          config.auto_provision_members
                            ? "bg-teal-500"
                            : "bg-gray-200"
                        }`}
                      >
                        <span
                          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                            config.auto_provision_members
                              ? "translate-x-5"
                              : "translate-x-0"
                          }`}
                        />
                      </button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleDirectorySync(config.id)}
                        isLoading={
                          triggerDirectorySync.isPending &&
                          triggerDirectorySync.variables?.configId === config.id
                        }
                        aria-label={`Sync directory for ${providerLabel}`}
                      >
                        <RotateCw className="h-4 w-4" />
                        Sync Directory
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
