// ─── Core Entities ───────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  display_name: string;
  account_type: "family" | "school" | "club";
  group_id: string | null;
  role: "owner" | "admin" | "member" | "viewer" | null;
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

export interface CreateGroupRequest {
  name: string;
  type: "family" | "school" | "club";
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
  date_of_birth?: string;
  age_verified?: boolean;
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
  snoozed_until?: string | null;
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

export interface BudgetThreshold {
  id: string;
  group_id: string;
  member_id: string | null;
  type: "soft" | "hard";
  amount: number;
  currency: string;
  notify_at: number[] | null;
  created_at: string;
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
  activity_trend: TrendDataPoint[];
  risk_breakdown: CategoryCount[];
  spend_trend: TrendDataPoint[];
}

export interface TrendDataPoint {
  date: string;
  count: number;
  amount: number;
}

export interface CategoryCount {
  category: string;
  count: number;
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
  trial_active: boolean;
  trial_days_remaining: number;
  trial_end: string | null;
  trial_locked: boolean;
}

export interface TrialStatus {
  is_active: boolean;
  is_trial: boolean;
  is_locked: boolean;
  days_remaining: number;
  trial_end: string | null;
  plan: string;
  contact_email: string;
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
  sms_enabled?: boolean;
}

export interface UpdateProfileRequest {
  display_name?: string;
  email?: string;
  phone_number?: string;
}

// ─── Consent ───────────────────────────────────────────────────────────────

export type ConsentType =
  | "coppa"
  | "gdpr"
  | "lgpd"
  | "au_privacy"
  | "monitoring"
  | "ai_interaction"
  | "data_collection";

export interface ConsentRecord {
  id: string;
  group_id: string;
  member_id: string;
  consent_type: ConsentType;
  parent_user_id: string | null;
  given_at: string;
  withdrawn_at: string | null;
  created_at: string;
}

export interface RecordConsentRequest {
  consent_type: ConsentType;
  evidence?: string;
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

// ─── Contact Inquiry ────────────────────────────────────────────────────────

export type EstimatedMembers = "10-50" | "50-200" | "200-500" | "500+";

export interface ContactInquiryRequest {
  organisation: string;
  contact_name: string;
  email: string;
  account_type: "school" | "club";
  estimated_members: EstimatedMembers;
  message?: string;
}

// ─── Blocking ──────────────────────────────────────────────────────────────

export interface BlockRule {
  id: string;
  group_id: string;
  member_id: string;
  platforms: string[] | null;
  reason: string | null;
  active: boolean;
  created_by: string;
  expires_at: string | null;
  created_at: string;
}

export interface BlockStatus {
  blocked: boolean;
  rules: BlockRule[];
}

// ─── Analytics ─────────────────────────────────────────────────────────────

export interface TrendData {
  group_id: string;
  activity: {
    direction: string;
    current_avg: number;
    previous_avg: number;
  };
  risk_events: {
    direction: string;
    current_count: number;
    previous_count: number;
  };
}

export interface UsagePattern {
  by_platform: Record<string, number>;
  by_hour: Record<string, number>;
  by_day_of_week: Record<string, number>;
  total_events: number;
}

export interface MemberBaseline {
  member_id: string;
  member_name: string;
  total_events: number;
  primary_platform: string;
  avg_daily: number;
}

// ─── Integrations ──────────────────────────────────────────────────────────

export interface SISConnection {
  id: string;
  group_id: string;
  provider: string;
  status: string;
  last_synced: string | null;
  created_at: string;
}

// ─── Compliance (Phase 8) ──────────────────────────────────────────────────

export interface AppealRecord {
  id: string;
  risk_event_id: string;
  status: string;
  reason: string;
  resolution: string | null;
  resolution_notes: string | null;
  created_at: string;
}

export interface TransparencyReport {
  classification_approach: string;
  categories: string[];
  data_sources: string[];
  rights: string[];
}
