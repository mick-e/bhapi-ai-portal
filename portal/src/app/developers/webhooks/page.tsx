"use client";

import { useState } from "react";
import {
  Webhook,
  Plus,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  Send,
  Trash2,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  useWebhooks,
  useCreateWebhook,
  useSendTestEvent,
  type WebhookEndpoint,
} from "@/hooks/use-developer-portal";

const WEBHOOK_EVENTS = [
  { id: "alert.created", label: "Alert Created", desc: "New risk alert for a member" },
  { id: "risk.scored", label: "Risk Scored", desc: "AI safety score computed for a session" },
  { id: "member.added", label: "Member Added", desc: "New member joined a group" },
  { id: "capture.ingested", label: "Capture Ingested", desc: "Session captured from extension" },
];

function EventBadge({ event }: { event: string }) {
  const colors: Record<string, string> = {
    "alert.created": "bg-red-50 text-red-700",
    "risk.scored": "bg-amber-50 text-amber-700",
    "member.added": "bg-green-50 text-green-700",
    "capture.ingested": "bg-blue-50 text-blue-700",
  };
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
        colors[event] ?? "bg-gray-50 text-gray-700"
      }`}
    >
      {event}
    </span>
  );
}

function AddWebhookForm({ onClose }: { onClose: () => void }) {
  const [url, setUrl] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [secret, setSecret] = useState("");
  const { mutate: createWebhook, isPending, isError } = useCreateWebhook();

  function toggleEvent(id: string) {
    setSelectedEvents((prev) =>
      prev.includes(id) ? prev.filter((e) => e !== id) : [...prev, id]
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url || selectedEvents.length === 0) return;
    createWebhook(
      { url, events: selectedEvents, secret: secret || undefined },
      { onSuccess: onClose }
    );
  }

  return (
    <Card className="mb-6">
      <h3 className="mb-4 font-semibold text-gray-900">Add Webhook Endpoint</h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="webhook-url"
            className="mb-1 block text-sm font-medium text-gray-700"
          >
            Endpoint URL
          </label>
          <input
            id="webhook-url"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://yourapp.com/webhooks/bhapi"
            required
            className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400"
          />
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-gray-700">
            Events to subscribe
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {WEBHOOK_EVENTS.map((ev) => (
              <label
                key={ev.id}
                className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors ${
                  selectedEvents.includes(ev.id)
                    ? "border-primary-300 bg-primary-50"
                    : "border-gray-200 bg-white hover:border-gray-300"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedEvents.includes(ev.id)}
                  onChange={() => toggleEvent(ev.id)}
                  className="mt-0.5 h-4 w-4 accent-primary-600"
                />
                <div>
                  <p className="text-sm font-medium text-gray-900">{ev.label}</p>
                  <p className="text-xs text-gray-500">{ev.desc}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label
            htmlFor="webhook-secret"
            className="mb-1 block text-sm font-medium text-gray-700"
          >
            Signing Secret{" "}
            <span className="font-normal text-gray-400">(optional)</span>
          </label>
          <input
            id="webhook-secret"
            type="text"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            placeholder="whsec_..."
            className="block w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400"
          />
          <p className="mt-1 text-xs text-gray-400">
            Used to verify HMAC-SHA256 signatures on incoming payloads.
          </p>
        </div>

        {isError && (
          <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            Failed to register webhook. Check your URL and try again.
          </div>
        )}

        <div className="flex gap-2">
          <Button
            type="submit"
            isLoading={isPending}
            disabled={!url || selectedEvents.length === 0}
          >
            Add Endpoint
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  );
}

function WebhookRow({ endpoint }: { endpoint: WebhookEndpoint }) {
  const { mutate: sendTest, isPending: testPending } = useSendTestEvent();
  const [testResult, setTestResult] = useState<boolean | null>(null);

  function handleTest() {
    sendTest(endpoint.id, {
      onSuccess: (delivery) => setTestResult(delivery.success),
      onError: () => setTestResult(false),
    });
  }

  return (
    <Card>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            {endpoint.is_active ? (
              <CheckCircle className="h-4 w-4 flex-shrink-0 text-green-500" />
            ) : (
              <XCircle className="h-4 w-4 flex-shrink-0 text-gray-300" />
            )}
            <p className="truncate font-mono text-sm font-medium text-gray-900">
              {endpoint.url}
            </p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {endpoint.events.map((ev) => (
              <EventBadge key={ev} event={ev} />
            ))}
          </div>
          <p className="mt-1 text-xs text-gray-400">
            Added {new Date(endpoint.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {testResult !== null && (
            <span
              className={`text-xs font-medium ${
                testResult ? "text-green-600" : "text-red-600"
              }`}
            >
              {testResult ? "Test delivered" : "Test failed"}
            </span>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={handleTest}
            isLoading={testPending}
          >
            <Send className="mr-1.5 h-3.5 w-3.5" />
            Test
          </Button>
          <button
            className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
            title="Delete webhook"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </Card>
  );
}

export default function WebhooksPage() {
  const { data, isLoading, isError } = useWebhooks();
  const [showForm, setShowForm] = useState(false);

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Webhooks</h1>
          <p className="mt-1 text-sm text-gray-500">
            Subscribe to real-time events from the Bhapi platform.
          </p>
        </div>
        {!showForm && (
          <Button onClick={() => setShowForm(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Webhook
          </Button>
        )}
      </div>

      {showForm && <AddWebhookForm onClose={() => setShowForm(false)} />}

      {/* Event reference */}
      <div className="mb-6 rounded-xl bg-gray-50 p-4">
        <p className="mb-3 text-sm font-semibold text-gray-700">
          Available Events
        </p>
        <div className="grid gap-2 sm:grid-cols-2">
          {WEBHOOK_EVENTS.map((ev) => (
            <div key={ev.id} className="flex items-start gap-2">
              <code className="rounded bg-white px-2 py-0.5 text-xs ring-1 ring-gray-200">
                {ev.id}
              </code>
              <span className="text-xs text-gray-600">{ev.desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Webhook list */}
      {isLoading && (
        <div className="flex h-32 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      )}

      {isError && (
        <div className="flex items-center gap-2 rounded-xl bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          Failed to load webhooks. Please refresh the page.
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {data?.items && data.items.length > 0 ? (
            <div className="space-y-3">
              <p className="text-sm font-medium text-gray-600">
                {data.total} endpoint{data.total !== 1 ? "s" : ""} registered
              </p>
              {data.items.map((endpoint) => (
                <WebhookRow key={endpoint.id} endpoint={endpoint} />
              ))}
            </div>
          ) : (
            <Card>
              <div className="py-12 text-center">
                <Webhook className="mx-auto mb-3 h-10 w-10 text-gray-300" />
                <p className="text-sm text-gray-500">
                  No webhook endpoints yet. Add one to start receiving events.
                </p>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
