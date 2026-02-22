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
  joined_at: string;
}

export interface CaptureEvent {
  id: string;
  group_id: string;
  member_id: string;
  member_name: string;
  provider: string;
  model: string;
  prompt_preview: string;
  response_preview: string;
  token_count: number;
  cost_usd: number;
  risk_level: "low" | "medium" | "high" | "critical";
  flagged: boolean;
  timestamp: string;
}

export interface RiskEvent {
  id: string;
  capture_event_id: string;
  group_id: string;
  member_id: string;
  member_name: string;
  category: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
  auto_action?: string;
  resolved: boolean;
  timestamp: string;
}

export interface Alert {
  id: string;
  group_id: string;
  type: "risk" | "spend" | "member" | "system";
  severity: "info" | "warning" | "error" | "critical";
  title: string;
  message: string;
  read: boolean;
  actioned: boolean;
  related_member_id?: string;
  related_event_id?: string;
  created_at: string;
}

export interface SpendSummary {
  group_id: string;
  period: "day" | "week" | "month";
  total_cost_usd: number;
  budget_usd: number;
  budget_remaining_usd: number;
  member_breakdown: {
    member_id: string;
    member_name: string;
    cost_usd: number;
  }[];
  provider_breakdown: {
    provider: string;
    cost_usd: number;
    request_count: number;
  }[];
}

export interface DashboardData {
  active_members: number;
  total_members: number;
  recent_activity: CaptureEvent[];
  alert_summary: {
    unread_count: number;
    critical_count: number;
    recent: Alert[];
  };
  spend_summary: SpendSummary;
  risk_summary: {
    total_events_today: number;
    high_severity_count: number;
    trend: "increasing" | "stable" | "decreasing";
  };
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ApiError {
  detail: string;
  status_code: number;
}
