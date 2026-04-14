"use client";

import { useState } from "react";
import {
  Users,
  Flag,
  Image,
  Video,
  Heart,
  MessageCircle,
  FileText,
  Loader2,
  AlertTriangle,
  RefreshCw,
  UserCheck,
  Clock,
  BarChart2,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useMembers } from "@/hooks/use-members";
import {
  useChildFeed,
  useChildContacts,
  useChildProfile,
  useFlagPost,
} from "@/hooks/use-social-monitor";
import type { SocialPost } from "@/hooks/use-social-monitor";
import { useToast } from "@/contexts/ToastContext";
import { useTranslations } from "@/contexts/LocaleContext";

export default function SocialFeedPage() {
  const t = useTranslations("socialFeed");
  const [selectedChildId, setSelectedChildId] = useState<string>("");
  const [flagPost, setFlagPost] = useState<SocialPost | null>(null);
  const [flagReason, setFlagReason] = useState("");

  const { data: membersData, isLoading: membersLoading } = useMembers();
  const children = (membersData?.items ?? []).filter(
    (m) => m.role === "member" && m.status === "active"
  );

  // Auto-select first child once loaded
  const effectiveChildId =
    selectedChildId || (children.length > 0 ? children[0].id : "");

  const {
    data: feedData,
    isLoading: feedLoading,
    isError: feedError,
    refetch: refetchFeed,
  } = useChildFeed(effectiveChildId);

  const {
    data: contactsData,
    isLoading: contactsLoading,
    isError: contactsError,
  } = useChildContacts(effectiveChildId);

  const { data: profile } = useChildProfile(effectiveChildId);

  const flagMutation = useFlagPost();
  const { addToast } = useToast();

  const posts = feedData?.items ?? [];
  const contacts = contactsData?.items ?? [];
  const approvedContacts = contacts.filter((c) => c.status === "approved");
  const pendingContacts = contacts.filter((c) => c.status === "pending");

  function handleFlagConfirm() {
    if (!flagPost || !flagReason.trim()) return;
    flagMutation.mutate(
      { postId: flagPost.id, reason: flagReason },
      {
        onSuccess: () => {
          addToast(t("postFlagged"), "success");
          setFlagPost(null);
          setFlagReason("");
        },
        onError: (err) => {
          addToast(
            (err as Error).message || t("failedFlag"),
            "error"
          );
        },
      }
    );
  }

  const selectedChild = children.find((c) => c.id === effectiveChildId);

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          {t("title")}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          {t("description")}
        </p>
      </div>

      {/* Child selector */}
      {membersLoading ? (
        <div className="mb-6 flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t("loadingMembers")}
        </div>
      ) : children.length === 0 ? (
        <div className="mb-6 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700 ring-1 ring-amber-200">
          {t("noChildren")}
        </div>
      ) : (
        <div className="mb-6 flex items-center gap-3">
          <label
            htmlFor="child-selector"
            className="text-sm font-medium text-gray-700"
          >
            {t("viewing")}:
          </label>
          <select
            id="child-selector"
            aria-label={t("selectChild")}
            value={effectiveChildId}
            onChange={(e) => setSelectedChildId(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            {children.map((child) => (
              <option key={child.id} value={child.id}>
                {child.display_name}
              </option>
            ))}
          </select>
        </div>
      )}

      {effectiveChildId && (
        <>
          {/* Activity Stats */}
          <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {profile?.post_count ?? posts.length}
                  </p>
                  <p className="text-sm text-gray-500">{t("totalPosts")}</p>
                </div>
              </div>
            </div>
            <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-pink-50">
                  <Heart className="h-5 w-5 text-pink-500" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {profile?.total_likes_received ??
                      posts.reduce((s, p) => s + p.like_count, 0)}
                  </p>
                  <p className="text-sm text-gray-500">{t("totalLikes")}</p>
                </div>
              </div>
            </div>
            <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-50">
                  <BarChart2 className="h-5 w-5 text-teal-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {profile?.total_comments_received ??
                      posts.reduce((s, p) => s + p.comment_count, 0)}
                  </p>
                  <p className="text-sm text-gray-500">
                    {t("totalComments")}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Social Feed Section */}
            <div className="lg:col-span-2">
              <Card>
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-base font-semibold text-gray-900">
                    {t("recentPosts")}
                  </h2>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => refetchFeed()}
                  >
                    <RefreshCw className="h-4 w-4" />
                    {t("refresh")}
                  </Button>
                </div>

                {feedLoading ? (
                  <div className="flex h-32 items-center justify-center">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                    <span className="ml-2 text-sm text-gray-500">
                      {t("loadingPosts")}
                    </span>
                  </div>
                ) : feedError ? (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <AlertTriangle className="h-8 w-8 text-amber-500" />
                    <p className="mt-2 text-sm text-gray-600">
                      {t("failedLoadPosts")}
                    </p>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="mt-3"
                      onClick={() => refetchFeed()}
                    >
                      {t("tryAgain")}
                    </Button>
                  </div>
                ) : posts.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <FileText className="h-10 w-10 text-gray-300" />
                    <p className="mt-3 text-sm font-medium text-gray-900">
                      {t("noPostsYet")}
                    </p>
                    <p className="mt-1 text-sm text-gray-500">
                      {selectedChild?.display_name ?? t("thisChild")} {t("noShareYet")}
                    </p>
                  </div>
                ) : (
                  <ul className="divide-y divide-gray-100" aria-label={t("postsLabel")}>
                    {posts.map((post) => (
                      <li key={post.id} className="py-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            {/* Moderation badge */}
                            <div className="mb-2 flex flex-wrap items-center gap-2">
                              <ModerationBadge
                                status={post.moderation_status}
                              />
                              {post.has_image && (
                                <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600">
                                  <Image className="h-3 w-3" />
                                  {t("image")}
                                </span>
                              )}
                              {post.has_video && (
                                <span className="inline-flex items-center gap-1 rounded-full bg-purple-50 px-2 py-0.5 text-xs text-purple-600">
                                  <Video className="h-3 w-3" />
                                  {t("video")}
                                </span>
                              )}
                            </div>
                            {/* Content */}
                            <p className="text-sm text-gray-800 line-clamp-3">
                              {post.content || (
                                <span className="italic text-gray-400">
                                  {t("noText")}
                                </span>
                              )}
                            </p>
                            {/* Engagement */}
                            <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
                              <span className="flex items-center gap-1">
                                <Heart className="h-3.5 w-3.5" />
                                {post.like_count}
                              </span>
                              <span className="flex items-center gap-1">
                                <MessageCircle className="h-3.5 w-3.5" />
                                {post.comment_count}
                              </span>
                              <span className="flex items-center gap-1">
                                <Clock className="h-3.5 w-3.5" />
                                {formatRelativeTime(post.created_at)}
                              </span>
                            </div>
                          </div>
                          {/* Flag button */}
                          <button
                            onClick={() => {
                              setFlagPost(post);
                              setFlagReason("");
                            }}
                            aria-label={`${t("flagPostBy")} ${post.author_name}`}
                            className="flex-shrink-0 rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-500"
                          >
                            <Flag className="h-4 w-4" />
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>

            {/* Contacts Section */}
            <div>
              <Card>
                <h2 className="mb-4 text-base font-semibold text-gray-900">
                  {t("contacts")}
                </h2>

                {contactsLoading ? (
                  <div className="flex h-24 items-center justify-center">
                    <Loader2 className="h-5 w-5 animate-spin text-primary" />
                  </div>
                ) : contactsError ? (
                  <p className="text-sm text-red-600">
                    {t("failedLoadContacts")}
                  </p>
                ) : contacts.length === 0 ? (
                  <div className="flex flex-col items-center py-8 text-center">
                    <Users className="h-8 w-8 text-gray-300" />
                    <p className="mt-2 text-sm text-gray-500">
                      {t("noContactsYet")}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Approved contacts */}
                    {approvedContacts.length > 0 && (
                      <div>
                        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-400">
                          {t("approved")} ({approvedContacts.length})
                        </p>
                        <ul className="space-y-2" aria-label={t("approvedContacts")}>
                          {approvedContacts.map((contact) => (
                            <li
                              key={contact.id}
                              className="flex items-center gap-2"
                            >
                              <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-green-100 text-xs font-semibold text-green-700">
                                {contact.contact_name.charAt(0).toUpperCase()}
                              </div>
                              <div className="min-w-0 flex-1">
                                <p className="truncate text-sm font-medium text-gray-900">
                                  {contact.contact_name}
                                </p>
                              </div>
                              <UserCheck className="h-4 w-4 flex-shrink-0 text-green-500" />
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Pending requests */}
                    {pendingContacts.length > 0 && (
                      <div>
                        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-400">
                          {t("pending")} ({pendingContacts.length})
                        </p>
                        <ul className="space-y-2" aria-label={t("pendingRequests")}>
                          {pendingContacts.map((contact) => (
                            <li
                              key={contact.id}
                              className="flex items-center gap-2"
                            >
                              <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-amber-100 text-xs font-semibold text-amber-700">
                                {contact.contact_name.charAt(0).toUpperCase()}
                              </div>
                              <div className="min-w-0 flex-1">
                                <p className="truncate text-sm font-medium text-gray-900">
                                  {contact.contact_name}
                                </p>
                                <p className="text-xs text-gray-500">
                                  {t("awaitingApproval")}
                                </p>
                              </div>
                              <Clock className="h-4 w-4 flex-shrink-0 text-amber-400" />
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </Card>
            </div>
          </div>
        </>
      )}

      {/* Flag Confirmation Modal */}
      {flagPost && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/30"
            onClick={() => setFlagPost(null)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="flag-modal-title"
              className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100">
                  <Flag className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <h2
                    id="flag-modal-title"
                    className="text-lg font-bold text-gray-900"
                  >
                    {t("flagThisPost")}
                  </h2>
                  <p className="text-sm text-gray-500">
                    {t("flagDesc")}
                  </p>
                </div>
              </div>

              <div className="mt-4">
                <p className="mb-3 rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-700 line-clamp-3">
                  {flagPost.content || t("noText")}
                </p>
                <label
                  htmlFor="flag-reason"
                  className="mb-1.5 block text-sm font-medium text-gray-700"
                >
                  {t("flagReason")}
                </label>
                <textarea
                  id="flag-reason"
                  rows={3}
                  placeholder={t("flagReasonPlaceholder")}
                  value={flagReason}
                  onChange={(e) => setFlagReason(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div className="mt-5 flex justify-end gap-3">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setFlagPost(null);
                    setFlagReason("");
                  }}
                >
                  {t("cancel")}
                </Button>
                <Button
                  onClick={handleFlagConfirm}
                  isLoading={flagMutation.isPending}
                  disabled={!flagReason.trim()}
                  className="bg-red-600 hover:bg-red-700"
                >
                  <Flag className="h-4 w-4" />
                  {t("flagPost")}
                </Button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function ModerationBadge({
  status,
}: {
  status: "pending" | "approved" | "rejected";
}) {
  const styles = {
    pending: "bg-amber-100 text-amber-700",
    approved: "bg-green-100 text-green-700",
    rejected: "bg-red-100 text-red-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {status}
    </span>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatRelativeTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60_000);
    const diffHours = Math.floor(diffMs / 3_600_000);
    const diffDays = Math.floor(diffMs / 86_400_000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch {
    return timestamp;
  }
}
