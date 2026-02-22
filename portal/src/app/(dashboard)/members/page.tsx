"use client";

import { useState } from "react";
import {
  Users,
  UserPlus,
  Search,
  MoreVertical,
  Shield,
  Mail,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";

interface MemberRow {
  id: string;
  name: string;
  email: string;
  role: string;
  status: "active" | "invited" | "suspended";
  lastActive: string;
  riskLevel: "low" | "medium" | "high";
}

const placeholderMembers: MemberRow[] = [
  {
    id: "1",
    name: "Sarah Johnson",
    email: "sarah@example.com",
    role: "Member",
    status: "active",
    lastActive: "2 min ago",
    riskLevel: "low",
  },
  {
    id: "2",
    name: "Tom Wilson",
    email: "tom@example.com",
    role: "Member",
    status: "active",
    lastActive: "15 min ago",
    riskLevel: "medium",
  },
  {
    id: "3",
    name: "Emma Davis",
    email: "emma@example.com",
    role: "Admin",
    status: "active",
    lastActive: "1 hour ago",
    riskLevel: "low",
  },
  {
    id: "4",
    name: "James Brown",
    email: "james@example.com",
    role: "Member",
    status: "active",
    lastActive: "3 hours ago",
    riskLevel: "high",
  },
  {
    id: "5",
    name: "Alex Chen",
    email: "alex@example.com",
    role: "Member",
    status: "invited",
    lastActive: "Never",
    riskLevel: "low",
  },
];

export default function MembersPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [showInviteModal, setShowInviteModal] = useState(false);

  const filteredMembers = placeholderMembers.filter(
    (m) =>
      m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div>
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Members</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your group members and their access
          </p>
        </div>
        <Button onClick={() => setShowInviteModal(true)}>
          <UserPlus className="h-4 w-4" />
          Invite Member
        </Button>
      </div>

      {/* Stats */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
              <Users className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {placeholderMembers.filter((m) => m.status === "active").length}
              </p>
              <p className="text-sm text-gray-500">Active members</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50">
              <Mail className="h-5 w-5 text-amber-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {
                  placeholderMembers.filter((m) => m.status === "invited")
                    .length
                }
              </p>
              <p className="text-sm text-gray-500">Pending invites</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-50">
              <Shield className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {placeholderMembers.length}
              </p>
              <p className="text-sm text-gray-500">Total members</p>
            </div>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="mb-4">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search members..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      {/* Members Table */}
      <Card>
        <div className="-mx-6 -my-4 overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Member
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Risk
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Last Active
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filteredMembers.map((member) => (
                <tr key={member.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-xs font-semibold text-primary">
                        {member.name.charAt(0)}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {member.name}
                        </p>
                        <p className="text-xs text-gray-500">{member.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                    {member.role}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <StatusBadge status={member.status} />
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <RiskBadge level={member.riskLevel} />
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {member.lastActive}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right">
                    <button className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
                      <MoreVertical className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Invite Modal */}
      {showInviteModal && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/30"
            onClick={() => setShowInviteModal(false)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
              <h2 className="text-lg font-bold text-gray-900">
                Invite a Member
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                Send an invitation to join your group
              </p>
              <div className="mt-4 space-y-4">
                <Input
                  label="Email address"
                  type="email"
                  placeholder="member@example.com"
                />
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">
                    Role
                  </label>
                  <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20">
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                    <option value="viewer">Viewer</option>
                  </select>
                </div>
              </div>
              <div className="mt-6 flex justify-end gap-3">
                <Button
                  variant="secondary"
                  onClick={() => setShowInviteModal(false)}
                >
                  Cancel
                </Button>
                <Button onClick={() => setShowInviteModal(false)}>
                  Send Invite
                </Button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: "active" | "invited" | "suspended" }) {
  const styles = {
    active: "bg-green-100 text-green-700",
    invited: "bg-amber-100 text-amber-700",
    suspended: "bg-red-100 text-red-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {status}
    </span>
  );
}

function RiskBadge({ level }: { level: "low" | "medium" | "high" }) {
  const styles = {
    low: "bg-green-100 text-green-700",
    medium: "bg-amber-100 text-amber-700",
    high: "bg-red-100 text-red-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${styles[level]}`}
    >
      {level}
    </span>
  );
}
