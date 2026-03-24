"use client";

import { useState } from "react";
import { Copy, CheckCircle, Key, Webhook, Zap, BookOpen } from "lucide-react";
import { Card } from "@/components/ui/Card";

// ─── Code samples ─────────────────────────────────────────────────────────────

const AUTH_SAMPLES = {
  python: `import httpx

# 1. Obtain an access token via OAuth 2.0
response = httpx.post("https://bhapi.ai/api/v1/platform/token", json={
    "grant_type": "authorization_code",
    "code": "<auth_code>",
    "client_id": "<your_client_id>",
    "client_secret": "<your_client_secret>",
    "redirect_uri": "https://yourapp.com/callback",
    "code_verifier": "<pkce_verifier>",
})
tokens = response.json()
access_token = tokens["access_token"]

# 2. Use the token in subsequent requests
headers = {"Authorization": f"Bearer {access_token}"}
data = httpx.get("https://bhapi.ai/api/v1/portal/dashboard", headers=headers).json()`,

  javascript: `// 1. Exchange authorization code for tokens
const tokenRes = await fetch("https://bhapi.ai/api/v1/platform/token", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    grant_type: "authorization_code",
    code: "<auth_code>",
    client_id: "<your_client_id>",
    client_secret: "<your_client_secret>",
    redirect_uri: "https://yourapp.com/callback",
    code_verifier: "<pkce_verifier>",
  }),
});
const { access_token } = await tokenRes.json();

// 2. Authenticate subsequent requests
const dashboard = await fetch("https://bhapi.ai/api/v1/portal/dashboard", {
  headers: { Authorization: \`Bearer \${access_token}\` },
}).then((r) => r.json());`,

  curl: `# 1. Exchange authorization code for tokens
curl -X POST https://bhapi.ai/api/v1/platform/token \\
  -H "Content-Type: application/json" \\
  -d '{
    "grant_type": "authorization_code",
    "code": "<auth_code>",
    "client_id": "<your_client_id>",
    "client_secret": "<your_client_secret>",
    "redirect_uri": "https://yourapp.com/callback",
    "code_verifier": "<pkce_verifier>"
  }'

# 2. Use the access token
curl https://bhapi.ai/api/v1/portal/dashboard \\
  -H "Authorization: Bearer <access_token>"`,
};

const RISK_SAMPLES = {
  python: `import httpx

headers = {"Authorization": "Bearer <access_token>"}

# List risk events for a group
risks = httpx.get(
    "https://bhapi.ai/api/v1/risk/events",
    params={"group_id": "<group_id>", "page_size": 20},
    headers=headers,
).json()

for event in risks["items"]:
    print(f"{event['severity']}: {event['platform']} — score {event['safety_score']}")`,

  javascript: `const headers = { Authorization: "Bearer <access_token>" };

const risks = await fetch(
  "https://bhapi.ai/api/v1/risk/events?group_id=<group_id>&page_size=20",
  { headers }
).then((r) => r.json());

risks.items.forEach((event) => {
  console.log(\`\${event.severity}: \${event.platform} — score \${event.safety_score}\`);
});`,

  curl: `curl "https://bhapi.ai/api/v1/risk/events?group_id=<group_id>&page_size=20" \\
  -H "Authorization: Bearer <access_token>"`,
};

// ─── Endpoint reference ───────────────────────────────────────────────────────

const ENDPOINT_GROUPS = [
  {
    label: "Authentication",
    icon: Key,
    color: "text-primary-600 bg-primary-50",
    endpoints: [
      { method: "POST", path: "/api/v1/platform/authorize", desc: "Request authorization code (PKCE)" },
      { method: "POST", path: "/api/v1/platform/token", desc: "Exchange code for access + refresh tokens" },
      { method: "POST", path: "/api/v1/platform/token/refresh", desc: "Refresh an expiring access token" },
      { method: "POST", path: "/api/v1/platform/token/revoke", desc: "Revoke a token (RFC 7009)" },
    ],
  },
  {
    label: "Groups & Members",
    icon: BookOpen,
    color: "text-teal-600 bg-teal-50",
    endpoints: [
      { method: "GET", path: "/api/v1/groups", desc: "List groups accessible by the token" },
      { method: "GET", path: "/api/v1/groups/{id}/members", desc: "List members in a group" },
      { method: "POST", path: "/api/v1/groups/{id}/invite", desc: "Invite a new member" },
    ],
  },
  {
    label: "Risk & Alerts",
    icon: Zap,
    color: "text-red-600 bg-red-50",
    endpoints: [
      { method: "GET", path: "/api/v1/risk/events", desc: "List risk events (paginated)" },
      { method: "GET", path: "/api/v1/risk/events/{id}", desc: "Get a single risk event" },
      { method: "POST", path: "/api/v1/risk/events/{id}/acknowledge", desc: "Acknowledge a risk event" },
      { method: "GET", path: "/api/v1/alerts", desc: "List alerts" },
    ],
  },
  {
    label: "Webhooks",
    icon: Webhook,
    color: "text-purple-600 bg-purple-50",
    endpoints: [
      { id: "wh-create", method: "POST", path: "/api/v1/platform/webhooks", desc: "Register a webhook endpoint" },
      { id: "wh-list", method: "GET", path: "/api/v1/platform/webhooks", desc: "List webhook endpoints" },
      { id: "wh-delete", method: "DELETE", path: "/api/v1/platform/webhooks/{id}", desc: "Delete a webhook endpoint" },
      { id: "wh-test", method: "POST", path: "/api/v1/platform/webhooks/{id}/test", desc: "Send a test ping event" },
      { id: "wh-deliveries", method: "GET", path: "/api/v1/platform/webhooks/{id}/deliveries", desc: "List delivery attempts" },
    ],
  },
];

// ─── Sub-components ───────────────────────────────────────────────────────────

type TabKey = "python" | "javascript" | "curl";

function CodeBlock({
  samples,
  title,
}: {
  samples: Record<TabKey, string>;
  title: string;
}) {
  const [activeTab, setActiveTab] = useState<TabKey>("python");
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(samples[activeTab]).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const tabs: { id: TabKey; label: string }[] = [
    { id: "python", label: "Python" },
    { id: "javascript", label: "JavaScript" },
    { id: "curl", label: "cURL" },
  ];

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200">
      <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-2">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-white text-gray-900 shadow-sm ring-1 ring-gray-200"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-gray-500 hover:bg-gray-200 transition-colors"
        >
          {copied ? (
            <CheckCircle className="h-3.5 w-3.5 text-green-500" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto bg-gray-900 p-4 text-xs text-gray-100">
        <code>{samples[activeTab]}</code>
      </pre>
    </div>
  );
}

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-blue-50 text-blue-700",
  POST: "bg-green-50 text-green-700",
  PUT: "bg-amber-50 text-amber-700",
  PATCH: "bg-amber-50 text-amber-700",
  DELETE: "bg-red-50 text-red-700",
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DocsPage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">API Documentation</h1>
        <p className="mt-1 text-sm text-gray-500">
          Integrate child safety into your applications using the Bhapi REST API.
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-4">
        {/* Sticky sidebar TOC */}
        <nav className="hidden lg:block">
          <div className="sticky top-8 space-y-1">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
              On this page
            </p>
            {[
              { href: "#authentication", label: "Authentication" },
              { href: "#oauth-flow", label: "OAuth 2.0 Flow" },
              { href: "#code-samples", label: "Code Samples" },
              { href: "#endpoints", label: "Endpoint Reference" },
              { href: "#rate-limits", label: "Rate Limiting" },
            ].map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="block rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
              >
                {item.label}
              </a>
            ))}
          </div>
        </nav>

        {/* Main content */}
        <div className="space-y-12 lg:col-span-3">
          {/* Authentication */}
          <section id="authentication">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">
              Authentication
            </h2>
            <Card>
              <div className="space-y-4 text-sm text-gray-700">
                <p>
                  The Bhapi API uses{" "}
                  <strong>OAuth 2.0 with PKCE</strong> for secure authorization.
                  All requests must include a Bearer token in the{" "}
                  <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs">
                    Authorization
                  </code>{" "}
                  header.
                </p>
                <div className="rounded-lg bg-primary-50 p-3 text-primary-800 ring-1 ring-primary-200">
                  <p className="font-medium">Base URL</p>
                  <code className="font-mono text-sm">https://bhapi.ai</code>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="mb-2 font-medium">All API calls require:</p>
                  <ul className="ml-4 list-disc space-y-1 text-gray-600">
                    <li>
                      <code className="font-mono text-xs">Authorization: Bearer &lt;access_token&gt;</code>
                    </li>
                    <li>
                      <code className="font-mono text-xs">Content-Type: application/json</code>{" "}
                      for POST/PUT
                    </li>
                  </ul>
                </div>
              </div>
            </Card>
          </section>

          {/* OAuth flow */}
          <section id="oauth-flow">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">
              OAuth 2.0 Flow
            </h2>
            <Card>
              <ol className="space-y-4 text-sm text-gray-700">
                {[
                  {
                    step: "1",
                    title: "Register your app",
                    desc: 'Create an OAuth client in the Developer Portal and note your client_id.',
                  },
                  {
                    step: "2",
                    title: "Generate PKCE pair",
                    desc: "Create a code_verifier (random 43-128 char string) and code_challenge (SHA-256 hash, base64url-encoded).",
                  },
                  {
                    step: "3",
                    title: "Redirect to authorize",
                    desc: "Send the user to /api/v1/platform/authorize with your client_id, redirect_uri, and code_challenge.",
                  },
                  {
                    step: "4",
                    title: "Exchange code for tokens",
                    desc: "POST /api/v1/platform/token with the authorization code and code_verifier to receive access + refresh tokens.",
                  },
                  {
                    step: "5",
                    title: "Refresh when needed",
                    desc: "Access tokens expire in 1 hour. Use /api/v1/platform/token/refresh to issue a new pair.",
                  },
                ].map((item) => (
                  <li key={item.step} className="flex gap-4">
                    <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-700">
                      {item.step}
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{item.title}</p>
                      <p className="text-gray-600">{item.desc}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </Card>
          </section>

          {/* Code samples */}
          <section id="code-samples">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">
              Code Samples
            </h2>
            <div className="space-y-6">
              <div>
                <p className="mb-2 text-sm font-medium text-gray-700">
                  OAuth token exchange
                </p>
                <CodeBlock samples={AUTH_SAMPLES as Record<TabKey, string>} title="Auth" />
              </div>
              <div>
                <p className="mb-2 text-sm font-medium text-gray-700">
                  Fetching risk events
                </p>
                <CodeBlock samples={RISK_SAMPLES as Record<TabKey, string>} title="Risk" />
              </div>
            </div>
          </section>

          {/* Endpoint reference */}
          <section id="endpoints">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">
              Endpoint Reference
            </h2>
            <div className="space-y-6">
              {ENDPOINT_GROUPS.map((group) => {
                const Icon = group.icon;
                return (
                  <div key={group.label}>
                    <div className="mb-3 flex items-center gap-2">
                      <div
                        className={`flex h-7 w-7 items-center justify-center rounded-lg ${group.color}`}
                      >
                        <Icon className="h-4 w-4" />
                      </div>
                      <h3 className="font-semibold text-gray-900">
                        {group.label}
                      </h3>
                    </div>
                    <div className="overflow-hidden rounded-xl border border-gray-200">
                      {group.endpoints.map((ep, i) => (
                        <div
                          key={"id" in ep ? ep.id : `${ep.method}-${ep.path}`}
                          className={`flex items-center gap-3 px-4 py-3 ${
                            i !== group.endpoints.length - 1
                              ? "border-b border-gray-100"
                              : ""
                          }`}
                        >
                          <span
                            className={`w-14 flex-shrink-0 rounded px-2 py-0.5 text-center text-xs font-semibold ${
                              METHOD_COLORS[ep.method] ?? "bg-gray-50 text-gray-700"
                            }`}
                          >
                            {ep.method}
                          </span>
                          <code className="flex-1 font-mono text-xs text-gray-700">
                            {ep.path}
                          </code>
                          <span className="hidden text-xs text-gray-500 sm:block">
                            {ep.desc}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Rate limiting */}
          <section id="rate-limits">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">
              Rate Limiting
            </h2>
            <Card>
              <p className="mb-4 text-sm text-gray-700">
                All API responses include rate limit headers so you can monitor
                your consumption in real time.
              </p>
              <div className="mb-4 overflow-hidden rounded-lg bg-gray-900 p-4 font-mono text-xs text-gray-100">
                <p className="text-gray-400"># Response headers</p>
                <p>X-RateLimit-Limit: 10000</p>
                <p>X-RateLimit-Remaining: 9843</p>
                <p>X-RateLimit-Reset: 1711324800</p>
                <p>Retry-After: 60 <span className="text-gray-500"># only on 429</span></p>
              </div>
              <div className="overflow-hidden rounded-xl border border-gray-200 text-sm">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50">
                      <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-600">
                        Tier
                      </th>
                      <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-600">
                        Daily Limit
                      </th>
                      <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-600">
                        Burst
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { tier: "Free", limit: "1,000", burst: "50 / min" },
                      { tier: "Starter", limit: "10,000", burst: "200 / min" },
                      { tier: "Growth", limit: "100,000", burst: "1,000 / min" },
                      { tier: "Enterprise", limit: "Unlimited", burst: "Custom" },
                    ].map((row, i) => (
                      <tr
                        key={row.tier}
                        className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}
                      >
                        <td className="px-4 py-2.5 font-medium text-gray-900">
                          {row.tier}
                        </td>
                        <td className="px-4 py-2.5 text-gray-700">
                          {row.limit}
                        </td>
                        <td className="px-4 py-2.5 text-gray-700">
                          {row.burst}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-xs text-gray-400">
                When you exceed your rate limit you receive a{" "}
                <code className="font-mono">429 Too Many Requests</code>{" "}
                response. Implement exponential back-off and respect the{" "}
                <code className="font-mono">Retry-After</code> header.
              </p>
            </Card>
          </section>
        </div>
      </div>
    </div>
  );
}
