/**
 * Moderation types for content review pipeline.
 */

export interface ModerationQueueItem {
  id: string;
  content_type: ContentType;
  content_id: string;
  content_preview: string;
  author_id: string;
  author_age_tier: '5-9' | '10-12' | '13-15';
  status: ModerationItemStatus;
  flags: ModerationFlag[];
  assigned_to: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export type ContentType = 'post' | 'comment' | 'message' | 'media' | 'profile';

export type ModerationItemStatus =
  | 'pending'
  | 'in_review'
  | 'approved'
  | 'rejected'
  | 'escalated';

export interface ModerationFlag {
  type: FlagType;
  confidence: number;
  details: string | null;
}

export type FlagType =
  | 'inappropriate_language'
  | 'bullying'
  | 'pii_exposure'
  | 'self_harm'
  | 'violence'
  | 'sexual_content'
  | 'csam'
  | 'spam'
  | 'misinformation'
  | 'other';

export interface ContentReport {
  id: string;
  reporter_id: string;
  content_type: ContentType;
  content_id: string;
  reason: ReportReason;
  description: string | null;
  status: ReportStatus;
  resolution: string | null;
  created_at: string;
  resolved_at: string | null;
}

export type ReportReason =
  | 'inappropriate'
  | 'bullying'
  | 'spam'
  | 'impersonation'
  | 'self_harm'
  | 'other';

export type ReportStatus = 'submitted' | 'under_review' | 'resolved' | 'dismissed';

export interface ModerationAction {
  id: string;
  queue_item_id: string;
  action: ActionType;
  moderator_id: string;
  reason: string;
  created_at: string;
}

export type ActionType =
  | 'approve'
  | 'reject'
  | 'remove'
  | 'warn_user'
  | 'suspend_user'
  | 'escalate'
  | 'report_ncmec';

export interface ModerationStats {
  pending_count: number;
  reviewed_today: number;
  average_review_time_seconds: number;
  escalated_count: number;
  auto_approved_count: number;
  auto_rejected_count: number;
}
