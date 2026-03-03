// ─── Core Entities ───────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  display_name: string;
  account_type: "family" | "school" | "club";
  group_id: string;
  role: "owner" | "admin" | "member" | "viewer";
  avatar_url?: string;
  created_at: string;
  updated_at: string;
}

export interface Group {
  id: string;
  name: string;
  account_type: "family" | "school" | "club";
  owner_id: string;
  member_count: number;
  plan: "free" | "starter" | "pro" | "enterprise";
  created_at: string;
  updated_at: string;
}

export interface GroupMember {
  id: string;
  group_id: string;
  user_id: string;
  display_name: string;
  email: string;
  role: "owner" | "admin" | "member" | "viewer";
  status: "active" | "invited" | "suspended";
  safety_profile?: string;
  avatar_url?: string;
  last_active?: string;
  risk_level?: "low" | "medium" | "high";
  joined_at: string;
}

// ─── Capture Events ─────────────────────────────────────────────────────────

export type EventType = "chat" | "code" | "image" | "document";

export interface CaptureEvent {
  id: string;
  group_id: string;
  member_id: string;
  member_name: string;
  provider: string;
  model: string;
  event_type: EventType;
  prompt_preview: string;
  response_preview: string;
  token_count: number;
  cost_usd: number;
  risk_level: "low" | "medium" | "high" | "critical";
  flagged: boolean;
  timestamp: string;
}

// ─── Risk Events ────────────────────────────────────────────────────────────

export type RiskSeverity = "low" | "medium" | "high" | "critical";

export interface RiskEvent {
  id: string;
  capture_event_id: string;
  group_id: string;
  member_id: string;
  member_name: string;
  category: string;
  severity: RiskSeverity;
  description: string;
  auto_action?: string;
  resolved: boolean;
  acknowledged: boolean;
  acknowledged_by?: string;
  acknowledged_at?: string;
  timestamp: string;
}

// ─── Alerts ─────────────────────────────────────────────────────────────────

export type AlertType = "risk" | "spend" | "member" | "system";
export type AlertSeverity = "info" | "warning" | "error" | "critical";

export interface Alert {
  id: string;
  group_id: string;
  type: AlertType;
  severity: AlertSeverity;
  title: string;
  message: string;
  member_name?: string;
  read: boolean;
  actioned: boolean;
  related_member_id?: string;
  related_event_id?: string;
  created_at: string;
}

// ─── Spend ──────────────────────────────────────────────────────────────────

export interface SpendRecord {
  id: string;
  group_id: string;
  member_id: string;
  member_name: string;
  provider: string;
  model: string;
  token_count: number;
  cost_usd: number;
  timestamp: string;
}

export interface ProviderBreakdown {
  provider: string;
  cost_usd: number;
  request_count: number;
  percentage: number;
}

export interface MemberSpendBreakdown {
  member_id: string;
  member_name: string;
  cost_usd: number;
  limit_usd: number;
}

export interface SpendSummary {
  group_id: string;
  period: "day" | "week" | "month";
  period_label: string;
  total_cost_usd: number;
  budget_usd: number;
  budget_remaining_usd: number;
  budget_used_percentage: number;
  avg_daily_cost_usd: number;
  active_spenders: number;
  total_members: number;
  over_budget_count: number;
  member_breakdown: MemberSpendBreakdown[];
  provider_breakdown: ProviderBreakdown[];
  records: SpendRecord[];
}

// ─── Reports ────────────────────────────────────────────────────────────────

export type ReportType = "safety" | "spend" | "activity" | "compliance";
export type ReportStatus = "ready" | "generating" | "failed";
export type ReportFormat = "pdf" | "csv" | "json";
export type ReportSchedule = "none" | "daily" | "weekly" | "monthly";

export interface Report {
  id: string;
  group_id: string;
  title: string;
  description: string;
  type: ReportType;
  status: ReportStatus;
  format: ReportFormat;
  period_start: string;
  period_end: string;
  download_url?: string;
  generated_at?: string;
  created_at: string;
}

export interface ReportScheduleConfig {
  type: ReportType;
  schedule: ReportSchedule;
  format: ReportFormat;
  recipients: string[];
}

export interface CreateReportRequest {
  type: ReportType;
  format: ReportFormat;
  period_start: string;
  period_end: string;
}

// ─── Dashboard ──────────────────────────────────────────────────────────────

export interface DashboardData {
  active_members: number;
  total_members: number;
  interactions_today: number;
  interactions_trend: string;
  recent_activity: CaptureEvent[];
  alert_summary: {
    unread_count: number;
    critical_count: number;
    recent: Alert[];
  };
  spend_summary: {
    today_usd: number;
    month_usd: number;
    budget_usd: number;
    budget_used_percentage: number;
    top_provider: string;
    top_provider_cost_usd: number;
    top_provider_percentage: number;
    top_member: string;
    top_member_cost_usd: number;
    top_member_percentage: number;
  };
  risk_summary: {
    total_events_today: number;
    high_severity_count: number;
    trend: "increasing" | "stable" | "decreasing";
  };
}

// ─── Settings ───────────────────────────────────────────────────────────────

export type SafetyLevel = "strict" | "moderate" | "permissive";

export interface GroupSettings {
  group_id: string;
  group_name: string;
  account_type: "family" | "school" | "club";
  safety_level: SafetyLevel;
  auto_block_critical: boolean;
  prompt_logging: boolean;
  pii_detection: boolean;
  notifications: NotificationPreferences;
  monthly_budget_usd: number;
  plan: "free" | "starter" | "pro" | "enterprise";
}

export interface NotificationPreferences {
  critical_safety: boolean;
  risk_warnings: boolean;
  spend_alerts: boolean;
  member_updates: boolean;
  weekly_digest: boolean;
  report_notifications: boolean;
}

export interface UpdateGroupSettingsRequest {
  group_name?: string;
  safety_level?: SafetyLevel;
  auto_block_critical?: boolean;
  prompt_logging?: boolean;
  pii_detection?: boolean;
  notifications?: Partial<NotificationPreferences>;
  monthly_budget_usd?: number;
}

export interface UpdateProfileRequest {
  display_name?: string;
  email?: string;
}

// ─── Auth ───────────────────────────────────────────────────────────────────

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

// ─── Pagination ─────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

// ─── Invitation ─────────────────────────────────────────────────────────────

export interface InviteMemberRequest {
  email: string;
  role: "admin" | "member" | "viewer";
}

export interface UpdateMemberRequest {
  role?: "admin" | "member" | "viewer";
  status?: "active" | "suspended";
  safety_profile?: string;
}

// ─── Risk Acknowledge ───────────────────────────────────────────────────────

export interface AcknowledgeRiskRequest {
  event_id: string;
  notes?: string;
}

// ─── API Keys ──────────────────────────────────────────────────────────────

export interface ApiKeyItem {
  id: string;
  name: string | null;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface CreateApiKeyRequest {
  name?: string;
}

export interface CreateApiKeyResponse extends ApiKeyItem {
  key: string;
}

// ─── Billing Checkout ──────────────────────────────────────────────────────

export interface CheckoutRequest {
  plan_type: string;
  billing_cycle: "monthly" | "annual";
}

export interface CheckoutResponse {
  session_id: string;
  url: string;
}

export interface PortalResponse {
  url: string;
}
