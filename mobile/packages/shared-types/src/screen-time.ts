/**
 * Screen Time types for the Bhapi Safety (parent) app.
 * API: /api/v1/screen-time/
 */

export type AppCategory =
  | 'social'
  | 'games'
  | 'education'
  | 'entertainment'
  | 'productivity'
  | 'all';

export type EnforcementAction =
  | 'hard_block'
  | 'warning_then_block'
  | 'warning_only'
  | 'allowed';

export type ExtensionRequestStatus = 'pending' | 'approved' | 'denied';

export type DayType = 'weekday' | 'weekend' | 'all';

export interface ScreenTimeRule {
  id: string;
  member_id: string;
  group_id: string;
  app_category: AppCategory;
  daily_limit_minutes: number;
  age_tier_enforcement: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface ScreenTimeSchedule {
  id: string;
  rule_id: string;
  day_type: DayType;
  blocked_start: string; // HH:MM format
  blocked_end: string;   // HH:MM format
  description: string | null;
}

export interface ExtensionRequest {
  id: string;
  member_id: string;
  rule_id: string;
  requested_minutes: number;
  status: ExtensionRequestStatus;
  requested_at: string;
  responded_at: string | null;
  responded_by: string | null;
  reason: string | null;
}

export interface UsageEvaluation {
  rule_id: string;
  category: AppCategory;
  used_minutes: number;
  limit_minutes: number;
  percent: number;
  enforcement_action: EnforcementAction;
}

export interface WeeklyReport {
  member_id: string;
  period_start: string;
  period_end: string;
  total_minutes: number;
  daily_average_minutes: number;
  days_with_data: number;
  daily_totals: DailyTotal[];
  category_totals: CategoryTotal[];
}

export interface DailyTotal {
  date: string;
  minutes: number;
}

export interface CategoryTotal {
  category: AppCategory;
  minutes: number;
}
