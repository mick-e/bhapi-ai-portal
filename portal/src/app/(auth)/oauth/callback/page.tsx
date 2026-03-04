"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle } from "lucide-react";
import { BhapiLogo } from "@/components/BhapiLogo";
import { setAuthToken } from "@/lib/auth";

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4">
          <BhapiLogo className="mx-auto h-10 w-auto animate-pulse" color="#FF6B35" />
          <p className="mt-4 text-sm text-gray-600">Loading...</p>
        </div>
      }
    >
      <OAuthCallbackContent />
    </Suspense>
  );
}

function OAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = searchParams.get("token");
    const state = searchParams.get("state");

    if (!token) {
      setError("Authentication failed — no token received.");
      return;
    }

    // Verify state matches what we stored (CSRF protection)
    const storedState = sessionStorage.getItem("oauth_state");
    if (storedState && state !== storedState) {
      setError("Authentication failed — state mismatch. Please try again.");
      sessionStorage.removeItem("oauth_state");
      return;
    }
    sessionStorage.removeItem("oauth_state");

    // Store token and redirect to dashboard
    setAuthToken(token);
    router.push("/dashboard");
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-md text-center">
          <AlertCircle className="mx-auto h-10 w-10 text-red-500" />
          <h1 className="mt-4 text-xl font-bold text-gray-900">
            Sign-in Failed
          </h1>
          <p className="mt-2 text-sm text-gray-600">{error}</p>
          <a
            href="/login"
            className="mt-4 inline-block text-sm font-medium text-primary-700 hover:text-primary-800"
          >
            Back to login
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md text-center">
        <BhapiLogo className="mx-auto h-10 w-auto animate-pulse" color="#FF6B35" />
        <h1 className="mt-4 text-xl font-bold text-gray-900">
          Completing sign-in...
        </h1>
        <p className="mt-2 text-sm text-gray-600">
          Please wait while we verify your account.
        </p>
      </div>
    </div>
  );
}
