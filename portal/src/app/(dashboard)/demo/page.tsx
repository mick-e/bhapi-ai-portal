"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Presentation, CheckCircle, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api-client";

interface DemoData {
  demo_token: string;
  expires_at: string;
  organisation: string;
}

export default function DemoPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [organisation, setOrganisation] = useState("");
  const [accountType, setAccountType] = useState<"school" | "club" | "enterprise">("school");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DemoData | null>(null);

  async function handleCreate() {
    if (!name.trim() || !email.trim() || !organisation.trim()) {
      setError("Please fill in all fields.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.post<DemoData>("/api/v1/portal/demo", {
        name,
        email,
        organisation,
        account_type: accountType,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create demo");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Request a Demo</h1>
        <p className="mt-1 text-sm text-gray-500">
          See Bhapi AI Portal in action with realistic sample data
        </p>
      </div>

      {result ? (
        <Card>
          <div className="text-center py-8">
            <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
            <h2 className="mt-4 text-xl font-bold text-gray-900">Demo Created!</h2>
            <p className="mt-2 text-sm text-gray-500">
              Your demo for {result.organisation} is ready.
            </p>
            <div className="mt-4 rounded-lg bg-gray-50 p-4 inline-block">
              <p className="text-xs text-gray-500">Demo Token</p>
              <code className="text-lg font-mono font-bold text-primary-700">{result.demo_token}</code>
            </div>
            <p className="mt-4 text-xs text-gray-400">
              Expires: {new Date(result.expires_at).toLocaleDateString()}
            </p>
            <Button className="mt-6" onClick={() => setResult(null)}>
              Create Another Demo
            </Button>
          </div>
        </Card>
      ) : (
        <div className="max-w-lg">
          <Card>
            <div className="space-y-4 p-2">
              <div className="flex items-center gap-3 mb-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100">
                  <Presentation className="h-5 w-5 text-primary-600" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Demo Details</h2>
                  <p className="text-xs text-gray-500">Fill in to generate a personalized demo</p>
                </div>
              </div>

              {error && (
                <div className="flex items-center gap-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
                  <AlertTriangle className="h-4 w-4" />
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700">Your name</label>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Smith" className="mt-1" />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="jane@school.edu" type="email" className="mt-1" />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Organisation</label>
                <Input value={organisation} onChange={(e) => setOrganisation(e.target.value)} placeholder="Springfield Unified" className="mt-1" />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Account type</label>
                <select
                  value={accountType}
                  onChange={(e) => setAccountType(e.target.value as "school" | "club" | "enterprise")}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="school">School</option>
                  <option value="club">Club</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>

              <Button onClick={handleCreate} isLoading={loading} className="w-full mt-2">
                Generate Demo
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
