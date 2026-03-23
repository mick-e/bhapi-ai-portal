/**
 * Screen Time React Query hooks for the Bhapi Safety (parent) app.
 * API: /api/v1/screen-time/
 *
 * Provides hooks for rules CRUD, usage evaluation, extension requests,
 * and weekly reports. All data fetching uses @tanstack/react-query.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  ScreenTimeRule,
  ScreenTimeSchedule,
  ExtensionRequest,
  UsageEvaluation,
  WeeklyReport,
  AppCategory,
  EnforcementAction,
  DayType,
} from '@bhapi/types';
import { ApiClient } from '@bhapi/api';

const apiClient = new ApiClient({ baseUrl: '' });

// ---- Query keys ----

const KEYS = {
  rules: (childId: string, groupId: string) => ['screen-time', 'rules', childId, groupId] as const,
  usage: (childId: string) => ['screen-time', 'usage', childId] as const,
  extensions: (childId: string) => ['screen-time', 'extensions', childId] as const,
  weeklyReport: (childId: string) => ['screen-time', 'weekly', childId] as const,
};

// ---- Rules ----

export function useScreenTimeRules(childId: string, groupId: string) {
  return useQuery<ScreenTimeRule[]>({
    queryKey: KEYS.rules(childId, groupId),
    queryFn: () =>
      apiClient.get<ScreenTimeRule[]>(
        `/api/v1/screen-time/rules?member_id=${childId}&group_id=${groupId}`
      ),
    enabled: Boolean(childId && groupId),
  });
}

export interface CreateRulePayload {
  member_id: string;
  group_id: string;
  app_category: AppCategory;
  daily_limit_minutes: number;
  age_tier_enforcement?: boolean;
  enabled?: boolean;
}

export function useCreateRule() {
  const queryClient = useQueryClient();
  return useMutation<ScreenTimeRule, Error, CreateRulePayload>({
    mutationFn: (payload) =>
      apiClient.post<ScreenTimeRule>('/api/v1/screen-time/rules', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['screen-time', 'rules'] });
    },
  });
}

export interface UpdateRulePayload {
  ruleId: string;
  daily_limit_minutes?: number;
  age_tier_enforcement?: boolean;
  enabled?: boolean;
}

export function useUpdateRule() {
  const queryClient = useQueryClient();
  return useMutation<ScreenTimeRule, Error, UpdateRulePayload>({
    mutationFn: ({ ruleId, ...body }) =>
      apiClient.put<ScreenTimeRule>(`/api/v1/screen-time/rules/${ruleId}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['screen-time', 'rules'] });
    },
  });
}

export function useDeleteRule() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (ruleId) =>
      apiClient.delete<void>(`/api/v1/screen-time/rules/${ruleId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['screen-time', 'rules'] });
    },
  });
}

// ---- Schedules ----

export interface CreateSchedulePayload {
  rule_id: string;
  day_type: DayType;
  blocked_start: string;
  blocked_end: string;
  description?: string;
}

export function useCreateSchedule() {
  const queryClient = useQueryClient();
  return useMutation<ScreenTimeSchedule, Error, CreateSchedulePayload>({
    mutationFn: (payload) =>
      apiClient.post<ScreenTimeSchedule>('/api/v1/screen-time/schedules', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['screen-time'] });
    },
  });
}

export function useDeleteSchedule() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (scheduleId) =>
      apiClient.delete<void>(`/api/v1/screen-time/schedules/${scheduleId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['screen-time'] });
    },
  });
}

// ---- Usage evaluation ----

export function useUsageEvaluation(childId: string) {
  return useQuery<UsageEvaluation[]>({
    queryKey: KEYS.usage(childId),
    queryFn: () =>
      apiClient.get<UsageEvaluation[]>(
        `/api/v1/screen-time/evaluate?member_id=${childId}`
      ),
    enabled: Boolean(childId),
    refetchInterval: 60_000, // refresh every 60 seconds
  });
}

// ---- Extension requests ----

export function useExtensionRequests(childId: string) {
  return useQuery<ExtensionRequest[]>({
    queryKey: KEYS.extensions(childId),
    queryFn: () =>
      apiClient.get<ExtensionRequest[]>(
        `/api/v1/screen-time/extensions?member_id=${childId}&status=pending`
      ),
    enabled: Boolean(childId),
  });
}

export interface RespondExtensionPayload {
  requestId: string;
  action: 'approve' | 'deny';
}

export function useRespondExtension() {
  const queryClient = useQueryClient();
  return useMutation<ExtensionRequest, Error, RespondExtensionPayload>({
    mutationFn: ({ requestId, action }) =>
      apiClient.post<ExtensionRequest>(
        `/api/v1/screen-time/extensions/${requestId}/respond`,
        { action }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['screen-time', 'extensions'] });
      queryClient.invalidateQueries({ queryKey: ['screen-time', 'usage'] });
    },
  });
}

// ---- Weekly report ----

export function useWeeklyReport(childId: string) {
  return useQuery<WeeklyReport>({
    queryKey: KEYS.weeklyReport(childId),
    queryFn: () =>
      apiClient.get<WeeklyReport>(
        `/api/v1/screen-time/weekly-report?member_id=${childId}`
      ),
    enabled: Boolean(childId),
  });
}
