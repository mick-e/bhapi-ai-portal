"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Users, GraduationCap, Building2 } from "lucide-react";
import { BhapiLogo } from "@/components/BhapiLogo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/use-auth";
import { contactApi } from "@/lib/api-client";
import type { EstimatedMembers } from "@/types";

type AccountType = "family" | "school" | "club";

const accountTypes: {
  value: AccountType;
  label: string;
  description: string;
  icon: React.ReactNode;
}[] = [
  {
    value: "family",
    label: "Family",
    description: "Protect your household",
    icon: <Users className="h-5 w-5" />,
  },
  {
    value: "school",
    label: "School",
    description: "Safeguard your students",
    icon: <GraduationCap className="h-5 w-5" />,
  },
  {
    value: "club",
    label: "Club",
    description: "Manage your organisation",
    icon: <Building2 className="h-5 w-5" />,
  },
];

const memberOptions: { value: EstimatedMembers; label: string }[] = [
  { value: "10-50", label: "10–50 members" },
  { value: "50-200", label: "50–200 members" },
  { value: "200-500", label: "200–500 members" },
  { value: "500+", label: "500+ members" },
];

export default function RegisterPage() {
  const { register, loginWithOAuth, isLoading, error } = useAuth();
  const [accountType, setAccountType] = useState<AccountType>("family");

  // Family registration fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");

  // Contact inquiry fields
  const [organisation, setOrganisation] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [estimatedMembers, setEstimatedMembers] = useState<EstimatedMembers>("10-50");
  const [message, setMessage] = useState("");
  const [inquiryLoading, setInquiryLoading] = useState(false);
  const [inquirySubmitted, setInquirySubmitted] = useState(false);

  // Privacy notice
  const [privacyAccepted, setPrivacyAccepted] = useState(true);

  const [formError, setFormError] = useState<string | null>(null);

  const isContactForm = accountType === "school" || accountType === "club";

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);

    if (!email || !password || !displayName) {
      setFormError("Please fill in all required fields.");
      return;
    }

    if (password.length < 8) {
      setFormError("Password must be at least 8 characters.");
      return;
    }

    if (!privacyAccepted) {
      setFormError("Please review and accept the privacy notice before creating an account.");
      return;
    }

    try {
      await register({
        email,
        password,
        display_name: displayName,
        account_type: accountType,
        privacy_notice_accepted: true,
      });
    } catch {
      // Error is handled by useAuth hook
    }
  }

  async function handleInquirySubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);

    if (!organisation || !contactName || !contactEmail) {
      setFormError("Please fill in all required fields.");
      return;
    }

    setInquiryLoading(true);
    try {
      await contactApi.submitInquiry({
        organisation,
        contact_name: contactName,
        email: contactEmail,
        account_type: accountType as "school" | "club",
        estimated_members: estimatedMembers,
        message: message || undefined,
      });
      setInquirySubmitted(true);
    } catch {
      setFormError("Something went wrong. Please try again or email sales@bhapi.ai directly.");
    } finally {
      setInquiryLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center">
          <Link href="/" className="flex items-center gap-2">
            <BhapiLogo className="h-10 w-auto" />
          </Link>
          <h1 className="mt-4 text-2xl font-bold text-gray-900">
            {isContactForm ? "Get in touch" : "Create your account"}
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            {isContactForm
              ? "Custom pricing for schools and clubs"
              : "Start protecting your group in minutes"}
          </p>
        </div>

        {/* Account Type Selector — always visible */}
        <div className="mb-6">
          <label className="mb-2 block text-sm font-medium text-gray-700">
            Account type
          </label>
          <div className="grid grid-cols-3 gap-3">
            {accountTypes.map((type) => (
              <button
                key={type.value}
                type="button"
                onClick={() => {
                  setAccountType(type.value);
                  setFormError(null);
                  setInquirySubmitted(false);
                }}
                className={`flex flex-col items-center rounded-lg border-2 px-3 py-4 text-center transition-colors ${
                  accountType === type.value
                    ? "border-primary bg-primary-50 text-primary"
                    : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"
                }`}
              >
                {type.icon}
                <span className="mt-1.5 text-sm font-semibold">
                  {type.label}
                </span>
                <span className="mt-0.5 text-xs opacity-75">
                  {type.description}
                </span>
              </button>
            ))}
          </div>
        </div>

        {(error || formError) && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">
            {error || formError}
          </div>
        )}

        {/* Contact Inquiry Form (School / Club) */}
        {isContactForm && !inquirySubmitted && (
          <form onSubmit={handleInquirySubmit} className="space-y-6">
            <Input
              label="Organisation name"
              type="text"
              placeholder="Springfield Elementary"
              value={organisation}
              onChange={(e) => setOrganisation(e.target.value)}
              required
            />

            <Input
              label="Contact name"
              type="text"
              placeholder="Your full name"
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
              autoComplete="name"
              required
            />

            <Input
              label="Email address"
              type="email"
              placeholder="you@example.com"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              autoComplete="email"
              required
            />

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Estimated number of members
              </label>
              <select
                value={estimatedMembers}
                onChange={(e) => setEstimatedMembers(e.target.value as EstimatedMembers)}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              >
                {memberOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Message <span className="font-normal text-gray-400">(optional)</span>
              </label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Tell us about your needs..."
                rows={3}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>

            <Button
              type="submit"
              size="lg"
              isLoading={inquiryLoading}
              className="w-full"
            >
              Request a Demo
            </Button>
          </form>
        )}

        {/* Inquiry success message */}
        {isContactForm && inquirySubmitted && (
          <div className="rounded-lg bg-green-50 px-6 py-8 text-center ring-1 ring-green-200">
            <h3 className="text-lg font-semibold text-green-800">
              Thank you for your interest!
            </h3>
            <p className="mt-2 text-sm text-green-700">
              Our team will be in touch within 1 business day. In the meantime, feel free to email us at{" "}
              <a href="mailto:sales@bhapi.ai" className="font-medium underline">
                sales@bhapi.ai
              </a>.
            </p>
          </div>
        )}

        {/* Family Registration — OAuth + Form */}
        {!isContactForm && (
          <>
            {/* SSO Buttons */}
            <div className="space-y-3">
              <button
                type="button"
                onClick={() => loginWithOAuth("google")}
                disabled={isLoading}
                className="flex w-full items-center justify-center gap-3 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                </svg>
                Continue with Google
              </button>

              <button
                type="button"
                onClick={() => loginWithOAuth("microsoft")}
                disabled={isLoading}
                className="flex w-full items-center justify-center gap-3 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                <svg className="h-5 w-5" viewBox="0 0 23 23" fill="none">
                  <path d="M11 0H0v11h11V0z" fill="#F25022" />
                  <path d="M23 0H12v11h11V0z" fill="#7FBA00" />
                  <path d="M11 12H0v11h11V12z" fill="#00A4EF" />
                  <path d="M23 12H12v11h11V12z" fill="#FFB900" />
                </svg>
                Continue with Microsoft
              </button>

              <button
                type="button"
                onClick={() => loginWithOAuth("apple")}
                disabled={isLoading}
                className="flex w-full items-center justify-center gap-3 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
                </svg>
                Continue with Apple
              </button>
            </div>

            {/* Divider */}
            <div className="my-6 flex items-center gap-4">
              <div className="h-px flex-1 bg-gray-200" />
              <span className="text-sm text-gray-400">or</span>
              <div className="h-px flex-1 bg-gray-200" />
            </div>
          </>
        )}

        {!isContactForm && (
          <form onSubmit={handleSubmit} className="space-y-6">
            <Input
              label="Display name"
              type="text"
              placeholder="Your name or group name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              autoComplete="name"
              required
            />

            <Input
              label="Email address"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />

            <Input
              label="Password"
              type="password"
              placeholder="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              helperText="Must be at least 8 characters"
              required
            />

            {/* COPPA 2026: Privacy notice consent */}
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <p className="mb-3 text-sm font-medium text-gray-800">
                Privacy &amp; Data Collection Notice
              </p>
              <ul className="mb-3 space-y-1.5 text-xs text-gray-600">
                <li>Your child&apos;s AI interactions will be collected and analyzed for safety</li>
                <li>Data may be shared with third-party providers (configurable in Privacy Settings)</li>
                <li>You can withdraw consent and request data deletion at any time</li>
              </ul>
              <label className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={privacyAccepted}
                  onChange={(e) => setPrivacyAccepted(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-xs text-gray-700">
                  I have read and accept the{" "}
                  <Link href="/legal/privacy" className="font-medium text-primary-700 underline">
                    Privacy Policy
                  </Link>
                  {" "}and understand how my family&apos;s data will be collected and used.
                </span>
              </label>
              <details className="mt-1 text-xs text-gray-500">
                <summary className="cursor-pointer text-primary-600 hover:text-primary-700">What this means</summary>
                <p className="mt-1">We collect data to monitor AI safety for your family. You can review and delete data at any time in Settings &gt; Privacy. Full details in our <Link href="/legal/privacy" className="underline">privacy policy</Link>.</p>
              </details>
            </div>

            <Button
              type="submit"
              size="lg"
              isLoading={isLoading}
              disabled={!privacyAccepted}
              className="w-full"
            >
              Create account
            </Button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-gray-600">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-primary-700 hover:text-primary-800"
          >
            Sign in
          </Link>
        </p>

        <p className="mt-4 text-center text-xs text-gray-400">
          By creating an account, you agree to our Terms of Service and Privacy
          Policy.
        </p>
      </div>
    </div>
  );
}
