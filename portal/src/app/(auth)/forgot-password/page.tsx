"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Shield, ArrowLeft, Mail } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api-client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!email) {
      setError("Please enter your email address.");
      return;
    }

    setIsLoading(true);
    try {
      await api.post("/api/v1/auth/forgot-password", { email });
      setIsSubmitted(true);
    } catch {
      // Show success anyway to prevent email enumeration
      setIsSubmitted(true);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center">
          <Link href="/" className="flex items-center gap-2">
            <Shield className="h-10 w-10 text-primary" />
            <span className="text-2xl font-bold text-gray-900">Bhapi</span>
          </Link>
        </div>

        {isSubmitted ? (
          /* Success State */
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-green-100">
              <Mail className="h-7 w-7 text-green-600" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">
              Check your email
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              If an account exists for <strong>{email}</strong>, we&apos;ve sent
              a password reset link. Please check your inbox and spam folder.
            </p>
            <div className="mt-8">
              <Link
                href="/login"
                className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:text-primary-700"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to sign in
              </Link>
            </div>
          </div>
        ) : (
          /* Form State */
          <>
            <div className="mb-6 text-center">
              <h1 className="text-2xl font-bold text-gray-900">
                Reset your password
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                Enter your email and we&apos;ll send you a reset link
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">
                  {error}
                </div>
              )}

              <Input
                label="Email address"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />

              <Button
                type="submit"
                size="lg"
                isLoading={isLoading}
                className="w-full"
              >
                Send reset link
              </Button>
            </form>

            <div className="mt-6 text-center">
              <Link
                href="/login"
                className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:text-primary-700"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to sign in
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
