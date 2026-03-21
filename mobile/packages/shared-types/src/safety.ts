/**
 * Safety and monitoring types for the Bhapi Safety (parent) app.
 */

export type AlertSource = 'ai' | 'social' | 'device';

export interface Alert {
  id: string;
  group_id: string;
  member_id: string;
  source: AlertSource;
  severity: AlertSeverity;
  category: AlertCategory;
  title: string;
  description: string;
  platform: string | null;
  status: AlertStatus;
  snoozed_until: string | null;
  created_at: string;
  updated_at: string;
}

export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';

export type AlertCategory =
  | 'pii_exposure'
  | 'harmful_content'
  | 'age_inappropriate'
  | 'emotional_dependency'
  | 'deepfake'
  | 'academic_integrity'
  | 'excessive_usage'
  | 'new_platform'
  | 'blocked_attempt'
  | 'safety_score_drop';

export type AlertStatus = 'unread' | 'read' | 'dismissed' | 'actioned';

export interface DashboardData {
  activity_summary: ActivitySummary;
  risk_overview: RiskOverview;
  recent_alerts: Alert[];
  platform_usage: PlatformUsage[];
  safety_scores: SafetyScore[];
  degraded_sections: string[];
}

export interface ActivitySummary {
  total_sessions: number;
  total_duration_minutes: number;
  platforms_used: number;
  last_active: string | null;
}

export interface RiskOverview {
  overall_score: number;
  trend: 'improving' | 'stable' | 'declining';
  high_risk_events: number;
  categories: RiskCategoryCount[];
}

export interface RiskCategoryCount {
  category: AlertCategory;
  count: number;
  severity: AlertSeverity;
}

export interface PlatformUsage {
  platform: string;
  session_count: number;
  duration_minutes: number;
  safety_score: number;
}

export interface SafetyScore {
  member_id: string;
  member_name: string;
  score: number;
  trend: 'improving' | 'stable' | 'declining';
  last_updated: string;
}

export interface CaptureEvent {
  id: string;
  group_id: string;
  member_id: string;
  platform: string;
  event_type: string;
  content_excerpt: string | null;
  risk_level: AlertSeverity | null;
  timestamp: string;
}

export interface TimeBudget {
  id: string;
  member_id: string;
  daily_limit_minutes: number;
  used_minutes: number;
  bedtime_start: string | null;
  bedtime_end: string | null;
  is_active: boolean;
}

export interface FamilyAgreement {
  id: string;
  group_id: string;
  version: string;
  signed_by_parent: boolean;
  signed_by_child: boolean;
  signed_at: string | null;
  content: string;
}
