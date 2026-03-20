"use client";

import { useState, useMemo } from "react";
import {
  Monitor,
  Shield,
  Rocket,
  Search,
  Plus,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Download,
  CheckCircle,
  XCircle,
  Clock,
  Laptop,
  Smartphone,
  Tablet,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/contexts/ToastContext";
import { useAuth } from "@/hooks/use-auth";
import {
  useSchoolDevices,
  useDeploymentStatus,
  useSchoolPolicies,
  useAddDevice,
  usePushPolicy,
  type SchoolDevice,
  type SchoolPolicy,
} from "@/hooks/use-school-admin";

type Tab = "devices" | "deployment" | "policies";

const statusColors: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  inactive: "bg-gray-100 text-gray-700",
  pending: "bg-amber-100 text-amber-700",
  error: "bg-red-100 text-red-700",
};

const statusIcons: Record<string, typeof CheckCircle> = {
  active: CheckCircle,
  inactive: XCircle,
  pending: Clock,
  error: AlertTriangle,
};

const osIcons: Record<string, typeof Laptop> = {
  windows: Laptop,
  macos: Laptop,
  linux: Laptop,
  chromeos: Laptop,
  ios: Smartphone,
  android: Smartphone,
  ipados: Tablet,
};

const enforcementColors: Record<string, string> = {
  warn: "bg-amber-100 text-amber-700",
  block: "bg-red-100 text-red-700",
  audit: "bg-blue-100 text-blue-700",
};

const policyTypeLabels: Record<string, string> = {
  acceptable_use: "Acceptable Use",
  data_handling: "Data Handling",
  model_access: "Model Access",
  cost_control: "Cost Control",
};

export default function SchoolAdminPage() {
  const { user } = useAuth();
  const { addToast } = useToast();
  const schoolId = user?.group_id ?? null;

  const [activeTab, setActiveTab] = useState<Tab>("devices");
  const [deviceSearch, setDeviceSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [showAddDeviceModal, setShowAddDeviceModal] = useState(false);
  const [showCreatePolicyModal, setShowCreatePolicyModal] = useState(false);

  // Add device form state
  const [newDeviceName, setNewDeviceName] = useState("");
  const [newDeviceOs, setNewDeviceOs] = useState("chromeos");
  const [newDeviceAssignee, setNewDeviceAssignee] = useState("");

  // Create policy form state
  const [policyName, setPolicyName] = useState("");
  const [policyDescription, setPolicyDescription] = useState("");
  const [policyType, setPolicyType] = useState("acceptable_use");
  const [policyEnforcement, setPolicyEnforcement] = useState("warn");

  const devicesQuery = useSchoolDevices(schoolId, {
    status: statusFilter || undefined,
    search: deviceSearch || undefined,
  });
  const deploymentQuery = useDeploymentStatus(schoolId);
  const policiesQuery = useSchoolPolicies(schoolId);

  const addDeviceMutation = useAddDevice(schoolId || "");
  const pushPolicyMutation = usePushPolicy(schoolId || "");

  const filteredDevices = useMemo(() => {
    const items = devicesQuery.data?.items ?? [];
    if (!deviceSearch && !statusFilter) return items;
    return items.filter((d) => {
      const matchesSearch =
        !deviceSearch ||
        d.device_name.toLowerCase().includes(deviceSearch.toLowerCase()) ||
        d.device_id.toLowerCase().includes(deviceSearch.toLowerCase()) ||
        (d.assigned_to?.toLowerCase().includes(deviceSearch.toLowerCase()) ?? false);
      const matchesStatus = !statusFilter || d.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [devicesQuery.data, deviceSearch, statusFilter]);

  function handleAddDevice() {
    if (!newDeviceName) return;
    addDeviceMutation.mutate(
      {
        device_name: newDeviceName,
        os: newDeviceOs,
        assigned_to: newDeviceAssignee || undefined,
      },
      {
        onSuccess: () => {
          addToast("Device added successfully", "success");
          setShowAddDeviceModal(false);
          setNewDeviceName("");
          setNewDeviceOs("chromeos");
          setNewDeviceAssignee("");
        },
        onError: (err) => {
          addToast(err.message || "Failed to add device", "error");
        },
      }
    );
  }

  function handleCreatePolicy() {
    if (!policyName) return;
    pushPolicyMutation.mutate(
      {
        name: policyName,
        description: policyDescription,
        policy_type: policyType,
        enforcement_level: policyEnforcement,
      },
      {
        onSuccess: () => {
          addToast("Policy created successfully", "success");
          setShowCreatePolicyModal(false);
          setPolicyName("");
          setPolicyDescription("");
          setPolicyType("acceptable_use");
          setPolicyEnforcement("warn");
        },
        onError: (err) => {
          addToast(err.message || "Failed to create policy", "error");
        },
      }
    );
  }

  function handleExportCsv() {
    const items = filteredDevices;
    if (items.length === 0) {
      addToast("No devices to export", "error");
      return;
    }
    const headers = ["Device ID", "Name", "OS", "Status", "Last Sync", "Assigned To"];
    const rows = items.map((d) => [
      d.device_id,
      d.device_name,
      d.os,
      d.status,
      d.last_sync || "Never",
      d.assigned_to || "Unassigned",
    ]);
    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "devices.csv";
    a.click();
    URL.revokeObjectURL(url);
    addToast("CSV exported", "success");
  }

  if (!schoolId) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">No school group found</p>
        <p className="mt-1 text-sm text-gray-500">
          Please create or join a school group to access the IT admin dashboard.
        </p>
      </div>
    );
  }

  const tabs: { key: Tab; label: string; icon: typeof Monitor }[] = [
    { key: "devices", label: "Devices", icon: Monitor },
    { key: "deployment", label: "Deployment", icon: Rocket },
    { key: "policies", label: "Policies", icon: Shield },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">School IT Admin</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage devices, monitor deployment, and configure policies
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1" role="tablist">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            role="tab"
            aria-selected={activeTab === key}
            aria-controls={`panel-${key}`}
            className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === key
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
            onClick={() => setActiveTab(key)}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Devices Tab */}
      {activeTab === "devices" && (
        <div id="panel-devices" role="tabpanel">
          {/* Toolbar */}
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-1 gap-3">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search devices..."
                  value={deviceSearch}
                  onChange={(e) => setDeviceSearch(e.target.value)}
                  aria-label="Search devices"
                  className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-3 text-sm text-gray-900 placeholder:text-gray-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                aria-label="Filter by status"
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                <option value="">All statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="pending">Pending</option>
                <option value="error">Error</option>
              </select>
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={handleExportCsv}>
                <Download className="h-4 w-4" />
                Export CSV
              </Button>
              <Button size="sm" onClick={() => setShowAddDeviceModal(true)}>
                <Plus className="h-4 w-4" />
                Add Device
              </Button>
            </div>
          </div>

          {/* Device Table */}
          {devicesQuery.isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="ml-3 text-sm text-gray-500">Loading devices...</span>
            </div>
          ) : devicesQuery.isError ? (
            <div className="flex h-64 flex-col items-center justify-center text-center">
              <AlertTriangle className="h-10 w-10 text-amber-500" />
              <p className="mt-3 text-sm font-medium text-gray-900">Failed to load devices</p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-4"
                onClick={() => devicesQuery.refetch()}
              >
                <RefreshCw className="h-4 w-4" />
                Try again
              </Button>
            </div>
          ) : filteredDevices.length === 0 ? (
            <Card>
              <div className="py-8 text-center">
                <Monitor className="mx-auto h-10 w-10 text-gray-300" />
                <p className="mt-3 text-sm text-gray-500">
                  {deviceSearch || statusFilter
                    ? "No devices match your filters"
                    : "No devices registered yet. Add your first device to get started."}
                </p>
              </div>
            </Card>
          ) : (
            <Card>
              <div className="-mx-6 -my-4 overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        Device
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        OS
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        Last Sync
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        Assigned To
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {filteredDevices.map((device) => {
                      const StatusIcon = statusIcons[device.status] || Clock;
                      const OsIcon = osIcons[device.os.toLowerCase()] || Laptop;
                      return (
                        <tr key={device.id}>
                          <td className="whitespace-nowrap px-6 py-4">
                            <div className="flex items-center gap-3">
                              <OsIcon className="h-5 w-5 text-gray-400" />
                              <div>
                                <p className="text-sm font-medium text-gray-900">{device.device_name}</p>
                                <p className="text-xs text-gray-500">{device.device_id}</p>
                              </div>
                            </div>
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                            {device.os}
                          </td>
                          <td className="whitespace-nowrap px-6 py-4">
                            <span
                              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColors[device.status] || "bg-gray-100 text-gray-700"}`}
                            >
                              <StatusIcon className="h-3 w-3" />
                              {device.status}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                            {device.last_sync
                              ? new Date(device.last_sync).toLocaleDateString()
                              : "Never"}
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                            {device.assigned_to || "Unassigned"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Deployment Tab */}
      {activeTab === "deployment" && (
        <div id="panel-deployment" role="tabpanel">
          {deploymentQuery.isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="ml-3 text-sm text-gray-500">Loading deployment status...</span>
            </div>
          ) : deploymentQuery.isError ? (
            <div className="flex h-64 flex-col items-center justify-center text-center">
              <AlertTriangle className="h-10 w-10 text-amber-500" />
              <p className="mt-3 text-sm font-medium text-gray-900">Failed to load deployment status</p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-4"
                onClick={() => deploymentQuery.refetch()}
              >
                <RefreshCw className="h-4 w-4" />
                Try again
              </Button>
            </div>
          ) : deploymentQuery.data ? (
            <div className="space-y-6">
              {/* Stats Cards */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
                <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
                  <p className="text-sm text-gray-500">Total Devices</p>
                  <p className="mt-1 text-2xl font-bold text-gray-900">
                    {deploymentQuery.data.total_devices}
                  </p>
                </div>
                <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
                  <p className="text-sm text-gray-500">Active</p>
                  <p className="mt-1 text-2xl font-bold text-green-600">
                    {deploymentQuery.data.active_devices}
                  </p>
                </div>
                <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
                  <p className="text-sm text-gray-500">Pending</p>
                  <p className="mt-1 text-2xl font-bold text-amber-600">
                    {deploymentQuery.data.pending_devices}
                  </p>
                </div>
                <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
                  <p className="text-sm text-gray-500">Errors</p>
                  <p className="mt-1 text-2xl font-bold text-red-600">
                    {deploymentQuery.data.error_devices}
                  </p>
                </div>
              </div>

              {/* Extension Coverage */}
              <Card title="Extension Coverage">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Extension installed</span>
                    <span className="text-sm font-semibold text-gray-900">
                      {deploymentQuery.data.extension_coverage_percent}%
                    </span>
                  </div>
                  <div className="h-3 w-full overflow-hidden rounded-full bg-gray-200">
                    <div
                      className="h-full rounded-full bg-primary-600 transition-all duration-500"
                      style={{
                        width: `${Math.min(100, deploymentQuery.data.extension_coverage_percent)}%`,
                      }}
                      role="progressbar"
                      aria-valuenow={deploymentQuery.data.extension_coverage_percent}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label="Extension coverage progress"
                    />
                  </div>
                  <p className="text-xs text-gray-500">
                    {deploymentQuery.data.active_devices} of{" "}
                    {deploymentQuery.data.total_devices} devices have the extension
                    installed and active
                  </p>
                </div>
              </Card>

              {/* Deployment Breakdown */}
              <Card title="Deployment Breakdown">
                <div className="space-y-3">
                  {[
                    { label: "Active", count: deploymentQuery.data.active_devices, color: "bg-green-500" },
                    { label: "Pending", count: deploymentQuery.data.pending_devices, color: "bg-amber-500" },
                    { label: "Inactive", count: deploymentQuery.data.inactive_devices, color: "bg-gray-400" },
                    { label: "Error", count: deploymentQuery.data.error_devices, color: "bg-red-500" },
                  ].map(({ label, count, color }) => (
                    <div key={label} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`h-3 w-3 rounded-full ${color}`} />
                        <span className="text-sm text-gray-700">{label}</span>
                      </div>
                      <span className="text-sm font-medium text-gray-900">{count}</span>
                    </div>
                  ))}
                </div>
              </Card>

              <p className="text-xs text-gray-400">
                Last updated:{" "}
                {new Date(deploymentQuery.data.last_updated).toLocaleString()}
              </p>
            </div>
          ) : null}
        </div>
      )}

      {/* Policies Tab */}
      {activeTab === "policies" && (
        <div id="panel-policies" role="tabpanel">
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Manage AI usage policies for your school
            </p>
            <Button size="sm" onClick={() => setShowCreatePolicyModal(true)}>
              <Plus className="h-4 w-4" />
              Create Policy
            </Button>
          </div>

          {policiesQuery.isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="ml-3 text-sm text-gray-500">Loading policies...</span>
            </div>
          ) : policiesQuery.isError ? (
            <div className="flex h-64 flex-col items-center justify-center text-center">
              <AlertTriangle className="h-10 w-10 text-amber-500" />
              <p className="mt-3 text-sm font-medium text-gray-900">Failed to load policies</p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-4"
                onClick={() => policiesQuery.refetch()}
              >
                <RefreshCw className="h-4 w-4" />
                Try again
              </Button>
            </div>
          ) : (policiesQuery.data ?? []).length === 0 ? (
            <Card>
              <div className="py-8 text-center">
                <Shield className="mx-auto h-10 w-10 text-gray-300" />
                <p className="mt-3 text-sm text-gray-500">
                  No policies created yet. Create your first AI usage policy to get started.
                </p>
              </div>
            </Card>
          ) : (
            <div className="space-y-3">
              {(policiesQuery.data ?? []).map((policy) => (
                <Card key={policy.id}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{policy.name}</p>
                      <p className="mt-0.5 text-xs text-gray-500">
                        {policy.description || policyTypeLabels[policy.policy_type] || policy.policy_type}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${enforcementColors[policy.enforcement_level] || "bg-gray-100 text-gray-700"}`}
                      >
                        {policy.enforcement_level}
                      </span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          policy.active
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {policy.active ? "Active" : "Inactive"}
                      </span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add Device Modal */}
      {showAddDeviceModal && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/30"
            onClick={() => setShowAddDeviceModal(false)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="add-device-title"
              className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
            >
              <h2 id="add-device-title" className="text-lg font-bold text-gray-900">
                Add Device
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                Register a new device for your school
              </p>
              <div className="mt-4 space-y-4">
                <Input
                  label="Device name"
                  placeholder="e.g. Lab Computer 01"
                  value={newDeviceName}
                  onChange={(e) => setNewDeviceName(e.target.value)}
                />
                <div className="w-full">
                  <label
                    htmlFor="device-os"
                    className="mb-1.5 block text-sm font-medium text-gray-700"
                  >
                    Operating system
                  </label>
                  <select
                    id="device-os"
                    value={newDeviceOs}
                    onChange={(e) => setNewDeviceOs(e.target.value)}
                    className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="chromeos">ChromeOS</option>
                    <option value="windows">Windows</option>
                    <option value="macos">macOS</option>
                    <option value="linux">Linux</option>
                    <option value="ios">iOS</option>
                    <option value="android">Android</option>
                    <option value="ipados">iPadOS</option>
                  </select>
                </div>
                <Input
                  label="Assigned to (optional)"
                  placeholder="e.g. Student name or room number"
                  value={newDeviceAssignee}
                  onChange={(e) => setNewDeviceAssignee(e.target.value)}
                />
              </div>
              <div className="mt-6 flex justify-end gap-3">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setShowAddDeviceModal(false);
                    setNewDeviceName("");
                    setNewDeviceOs("chromeos");
                    setNewDeviceAssignee("");
                  }}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleAddDevice}
                  isLoading={addDeviceMutation.isPending}
                  disabled={!newDeviceName}
                >
                  Add Device
                </Button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Create Policy Modal */}
      {showCreatePolicyModal && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/30"
            onClick={() => setShowCreatePolicyModal(false)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="create-policy-title"
              className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
            >
              <h2 id="create-policy-title" className="text-lg font-bold text-gray-900">
                Create Policy
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                Define a new AI usage policy for your school
              </p>
              <div className="mt-4 space-y-4">
                <Input
                  label="Policy name"
                  placeholder="e.g. No AI during exams"
                  value={policyName}
                  onChange={(e) => setPolicyName(e.target.value)}
                />
                <Input
                  label="Description"
                  placeholder="Describe the purpose of this policy"
                  value={policyDescription}
                  onChange={(e) => setPolicyDescription(e.target.value)}
                />
                <div className="w-full">
                  <label
                    htmlFor="policy-type"
                    className="mb-1.5 block text-sm font-medium text-gray-700"
                  >
                    Policy type
                  </label>
                  <select
                    id="policy-type"
                    value={policyType}
                    onChange={(e) => setPolicyType(e.target.value)}
                    className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="acceptable_use">Acceptable Use</option>
                    <option value="data_handling">Data Handling</option>
                    <option value="model_access">Model Access</option>
                    <option value="cost_control">Cost Control</option>
                  </select>
                </div>
                <div className="w-full">
                  <label
                    htmlFor="policy-enforcement"
                    className="mb-1.5 block text-sm font-medium text-gray-700"
                  >
                    Enforcement level
                  </label>
                  <select
                    id="policy-enforcement"
                    value={policyEnforcement}
                    onChange={(e) => setPolicyEnforcement(e.target.value)}
                    className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="warn">Warn</option>
                    <option value="block">Block</option>
                    <option value="audit">Audit</option>
                  </select>
                </div>
              </div>
              <div className="mt-6 flex justify-end gap-3">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setShowCreatePolicyModal(false);
                    setPolicyName("");
                    setPolicyDescription("");
                    setPolicyType("acceptable_use");
                    setPolicyEnforcement("warn");
                  }}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleCreatePolicy}
                  isLoading={pushPolicyMutation.isPending}
                  disabled={!policyName}
                >
                  Create Policy
                </Button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
