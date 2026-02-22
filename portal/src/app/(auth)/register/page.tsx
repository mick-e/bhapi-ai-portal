"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Shield, Users, GraduationCap, Building2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/use-auth";

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

export default function RegisterPage() {
  const { register, isLoading, error } = useAuth();
  const [accountType, setAccountType] = useState<AccountType>("family");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

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

    try {
      await register({
        email,
        password,
        display_name: displayName,
        account_type: accountType,
      });
    } catch {
      // Error is handled by useAuth hook
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center">
          <Link href="/" className="flex items-center gap-2">
            <Shield className="h-10 w-10 text-primary" />
            <span className="text-2xl font-bold text-gray-900">Bhapi</span>
          </Link>
          <h1 className="mt-4 text-2xl font-bold text-gray-900">
            Create your account
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            Start protecting your group in minutes
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {(error || formError) && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">
              {error || formError}
            </div>
          )}

          {/* Account Type Selector */}
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Account type
            </label>
            <div className="grid grid-cols-3 gap-3">
              {accountTypes.map((type) => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => setAccountType(type.value)}
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

          <Button
            type="submit"
            size="lg"
            isLoading={isLoading}
            className="w-full"
          >
            Create account
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-primary hover:text-primary-700"
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
