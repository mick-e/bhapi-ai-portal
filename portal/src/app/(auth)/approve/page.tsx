"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ApproveChildResponse {
  child_id: string;
  group_id: string;
}

interface ApiErrorBody {
  detail?: string;
  message?: string;
}

type ApprovalState =
  | { stage: "pending" }
  | { stage: "loading" }
  | { stage: "success"; data: ApproveChildResponse }
  | { stage: "error"; message: string };

// ---------------------------------------------------------------------------
// Inner component — reads query params safely inside Suspense
// ---------------------------------------------------------------------------

function ApproveContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [state, setState] = useState<ApprovalState>({ stage: "pending" });

  const handleAction = async (action: "approve" | "deny") => {
    if (!token) {
      setState({ stage: "error", message: "Invalid approval link — no token found." });
      return;
    }

    if (action === "deny") {
      setState({ stage: "error", message: "You have denied this request. No changes have been made." });
      return;
    }

    setState({ stage: "loading" });

    try {
      const res = await fetch("/api/v1/auth/approve-child", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });

      if (!res.ok) {
        const body: ApiErrorBody = await res.json().catch(() => ({}));
        const msg =
          body.detail ??
          body.message ??
          (res.status === 404
            ? "Approval link not found. It may have been already used or never existed."
            : res.status === 422
            ? "This approval link is invalid or has expired."
            : "Something went wrong. Please try again.");
        setState({ stage: "error", message: msg });
        return;
      }

      const data: ApproveChildResponse = await res.json();
      setState({ stage: "success", data });
    } catch {
      setState({ stage: "error", message: "Unable to reach the server. Please check your connection." });
    }
  };

  // ── Render helpers ──────────────────────────────────────────────────────

  if (!token) {
    return (
      <ErrorCard message="This approval link is missing a token. Please check the email you received and click the link again." />
    );
  }

  if (state.stage === "success") {
    return <SuccessCard />;
  }

  if (state.stage === "error") {
    return <ErrorCard message={state.message} />;
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div
          className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full"
          style={{ backgroundColor: "#FFF3ED" }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#FF6B35"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Parental Approval Request</h1>
        <p className="mt-2 text-gray-600">
          Your child would like to join your Bhapi family group. Review the request below and
          approve or deny it.
        </p>
      </div>

      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700">
        <p>
          <span className="font-semibold">What happens when you approve:</span>
        </p>
        <ul className="mt-2 list-inside list-disc space-y-1">
          <li>Your child will be added to your family group on Bhapi.</li>
          <li>You will be able to monitor their AI activity and set safety rules.</li>
          <li>Your child will be notified and can log into the Safety app.</li>
        </ul>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          onClick={() => handleAction("approve")}
          disabled={state.stage === "loading"}
          className="flex-1 rounded-lg px-6 py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-60"
          style={{ backgroundColor: "#FF6B35" }}
        >
          {state.stage === "loading" ? "Approving…" : "Approve"}
        </button>
        <button
          onClick={() => handleAction("deny")}
          disabled={state.stage === "loading"}
          className="flex-1 rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-60"
        >
          Deny
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SuccessCard() {
  return (
    <div className="space-y-6 text-center">
      <div
        className="mx-auto flex h-16 w-16 items-center justify-center rounded-full"
        style={{ backgroundColor: "#F0FDF9" }}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#0D9488"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>

      <div>
        <h2 className="text-2xl font-bold text-gray-900">Approved!</h2>
        <p className="mt-2 text-gray-600">
          Your child has been added to your Bhapi family group. They can now log into the Bhapi
          Safety app.
        </p>
      </div>

      <div className="rounded-lg border border-teal-100 bg-teal-50 p-5">
        <p className="mb-3 text-sm font-semibold text-teal-800">Download the Bhapi Safety App</p>
        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <a
            href="https://apps.apple.com/app/bhapi-safety/id0000000000"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
            </svg>
            App Store
          </a>
          <a
            href="https://play.google.com/store/apps/details?id=com.bhapi.safety"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="m3.18 23.76 11-6.35-2.54-2.54zM.5 1.93v20.14l11-10.07zM14.82 12 3.18.24l8.46 8.75zm2.7-10.07-3.52 2.03 2.54 2.54 3.52-2.03z" />
            </svg>
            Google Play
          </a>
        </div>
      </div>

      <p className="text-xs text-gray-500">
        You can manage your child&apos;s permissions at any time from your Bhapi dashboard at{" "}
        <a href="https://bhapi.ai" className="underline" style={{ color: "#FF6B35" }}>
          bhapi.ai
        </a>
        .
      </p>
    </div>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="space-y-4 text-center">
      <div
        className="mx-auto flex h-16 w-16 items-center justify-center rounded-full"
        style={{ backgroundColor: "#FEF2F2" }}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#DC2626"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <h2 className="text-xl font-bold text-gray-900">Something went wrong</h2>
      <p className="text-gray-600">{message}</p>
      <p className="text-sm text-gray-500">
        Need help?{" "}
        <a href="mailto:support@bhapi.ai" className="underline" style={{ color: "#FF6B35" }}>
          Contact support
        </a>
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page — wraps inner component in Suspense (required for useSearchParams)
// ---------------------------------------------------------------------------

export default function ApprovePage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-sm ring-1 ring-gray-200">
        {/* Logo */}
        <div className="mb-8 flex justify-center">
          <img src="/logo.png" alt="Bhapi" style={{ height: 32 }} />
        </div>

        <Suspense
          fallback={
            <div className="flex flex-col items-center gap-3 py-8">
              <div
                className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200"
                style={{ borderTopColor: "#FF6B35" }}
              />
              <p className="text-sm text-gray-500">Loading…</p>
            </div>
          }
        >
          <ApproveContent />
        </Suspense>
      </div>
    </div>
  );
}
