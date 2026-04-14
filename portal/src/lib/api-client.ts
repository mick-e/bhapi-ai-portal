import type {
  AcademicReport,
  AnomalyResponse,
  ApiError,
  ApiKeyItem,
  AppealRecord,
  BlockApproval,
  BlockEffectiveness,
  BlockRule,
  BlockStatus,
  CheckoutRequest,
  CheckoutResponse,
  ChildDashboard,
  ChildSelfView,
  ContactInquiryRequest,
  ConversationSummary,
  CreateApiKeyRequest,
  CreateApiKeyResponse,
  CreateGroupRequest,
  DashboardData,
  DeepfakeGuidance,
  DeviceSessionSummary,
  Group,
  GroupMember,
  IntentClassification,
  InviteMemberRequest,
  MemberVisibility,
  UpdateMemberRequest,
  CaptureEvent,
  MemberBaseline,
  PeerComparisonResponse,
  PlatformSafetyRating,
  PlatformSafetyRecommendation,
  RewardItem,
  RiskEvent,
  AcknowledgeRiskRequest,
  Alert,
  SetChildSelfViewRequest,
  SetVisibilityRequest,
  SISConnection,
  SSOConfig,
  SpendSummary,
  SpendRecord,
  Report,
  CreateReportRequest,
  ReportScheduleConfig,
  GroupSettings,
  UpdateGroupSettingsRequest,
  UpdateProfileRequest,
  TrendData,
  TransparencyReport,
  TrialStatus,
  UsagePattern,
  User,
  BudgetThreshold,
  ConsentRecord,
  RecordConsentRequest,
  PaginatedResponse,
  PortalResponse,
  PlansResponse,
  SubscriptionStatus,
} from "@/types";

// ─── Base Client ────────────────────────────────────────────────────────────

const BASE_URL = typeof window !== "undefined" ? "" : "http://localhost:8000";

export class ApiRequestError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiRequestError";
    this.status = status;
    this.detail = detail;
  }
}

function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("bhapi_auth_token");
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const token = getAuthToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    let detail = "An unexpected error occurred";
    try {
      const errorBody = await response.json();
      const raw = errorBody.detail ?? errorBody.message;
      if (typeof raw === "string") {
        detail = raw;
      } else if (Array.isArray(raw)) {
        // FastAPI validation errors: [{loc: [...], msg: "...", type: "..."}]
        detail = raw.map((e: { msg?: string }) => e.msg || String(e)).join("; ");
      } else if (raw) {
        detail = String(raw);
      }
    } catch {
      detail = response.statusText || detail;
    }

    // Clear stale auth and redirect to login on token expiry
    if (response.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("bhapi_auth_token");
      localStorage.removeItem("bhapi_user");
      window.location.href = "/login";
      return undefined as T;
    }

    // Redirect to billing when trial has expired
    if (response.status === 403 && typeof window !== "undefined") {
      try {
        const body = await response.clone().json();
        if (body?.code === "TRIAL_EXPIRED") {
          window.location.href = "/settings?tab=billing";
          return undefined as T;
        }
      } catch {
        // Not a JSON body — fall through to default error
      }
    }

    throw new ApiRequestError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  get<T>(path: string): Promise<T> {
    return apiFetch<T>(path, { method: "GET" });
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return apiFetch<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  put<T>(path: string, body?: unknown): Promise<T> {
    return apiFetch<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  patch<T>(path: string, body?: unknown): Promise<T> {
    return apiFetch<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  delete<T>(path: string): Promise<T> {
    return apiFetch<T>(path, { method: "DELETE" });
  },
};

// ─── Helper: build query string ─────────────────────────────────────────────

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== ""
  );
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");
}

// ─── Groups ─────────────────────────────────────────────────────────────────

export const groupsApi = {
  create(data: CreateGroupRequest): Promise<Group> {
    return api.post<Group>("/api/v1/groups", data);
  },
};

// ─── Dashboard ──────────────────────────────────────────────────────────────

export const dashboardApi = {
  getSummary(): Promise<DashboardData> {
    return api.get<DashboardData>("/api/v1/portal/dashboard");
  },
};

// ─── Members ────────────────────────────────────────────────────────────────

export const membersApi = {
  list(groupId: string, params?: { page?: number; page_size?: number; search?: string }): Promise<PaginatedResponse<GroupMember>> {
    const query = qs({
      page: params?.page,
      page_size: params?.page_size,
      search: params?.search,
    });
    return api.get<PaginatedResponse<GroupMember>>(`/api/v1/groups/${groupId}/members${query}`);
  },

  get(groupId: string, memberId: string): Promise<GroupMember> {
    return api.get<GroupMember>(`/api/v1/groups/${groupId}/members/${memberId}`);
  },

  invite(groupId: string, data: InviteMemberRequest): Promise<GroupMember> {
    return api.post<GroupMember>(`/api/v1/groups/${groupId}/members`, data);
  },

  update(groupId: string, memberId: string, data: UpdateMemberRequest): Promise<GroupMember> {
    return api.patch<GroupMember>(`/api/v1/groups/${groupId}/members/${memberId}`, data);
  },

  remove(groupId: string, memberId: string): Promise<void> {
    return api.delete<void>(`/api/v1/groups/${groupId}/members/${memberId}`);
  },

  recordConsent(
    groupId: string,
    memberId: string,
    data: RecordConsentRequest
  ): Promise<ConsentRecord> {
    return api.post<ConsentRecord>(
      `/api/v1/groups/${groupId}/members/${memberId}/consent`,
      data
    );
  },
};

// ─── Activity / Capture Events ──────────────────────────────────────────────

export const activityApi = {
  list(params?: {
    page?: number;
    page_size?: number;
    member_id?: string;
    risk_level?: string;
    provider?: string;
    event_type?: string;
    search?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<PaginatedResponse<CaptureEvent>> {
    const query = qs({
      page: params?.page,
      page_size: params?.page_size,
      member_id: params?.member_id,
      risk_level: params?.risk_level,
      provider: params?.provider,
      event_type: params?.event_type,
      search: params?.search,
      start_date: params?.start_date,
      end_date: params?.end_date,
    });
    return api.get<PaginatedResponse<CaptureEvent>>(`/api/v1/capture/events${query}`);
  },

  get(eventId: string): Promise<CaptureEvent> {
    return api.get<CaptureEvent>(`/api/v1/capture/events/${eventId}`);
  },
};

// ─── Risk Events ────────────────────────────────────────────────────────────

export const riskApi = {
  list(params?: {
    page?: number;
    page_size?: number;
    severity?: string;
    category?: string;
    resolved?: boolean;
    member_id?: string;
  }): Promise<PaginatedResponse<RiskEvent>> {
    const query = qs({
      page: params?.page,
      page_size: params?.page_size,
      severity: params?.severity,
      category: params?.category,
      acknowledged: params?.resolved,
      member_id: params?.member_id,
    });
    return api.get<PaginatedResponse<RiskEvent>>(`/api/v1/risk/events${query}`);
  },

  acknowledge(data: AcknowledgeRiskRequest): Promise<RiskEvent> {
    return api.post<RiskEvent>(`/api/v1/risk/events/${data.event_id}/acknowledge`, data);
  },

  getDeepfakeGuidance(): Promise<DeepfakeGuidance> {
    return api.get<DeepfakeGuidance>("/api/v1/risk/deepfake-guidance");
  },
};

// ─── Alerts ─────────────────────────────────────────────────────────────────

export const alertsApi = {
  list(params?: {
    page?: number;
    page_size?: number;
    severity?: string;
    type?: string;
    read?: boolean;
    start_date?: string;
    end_date?: string;
  }): Promise<PaginatedResponse<Alert>> {
    const query = qs({
      page: params?.page,
      page_size: params?.page_size,
      severity: params?.severity,
      type: params?.type,
      read: params?.read,
      start_date: params?.start_date,
      end_date: params?.end_date,
    });
    return api.get<PaginatedResponse<Alert>>(`/api/v1/alerts${query}`);
  },

  markRead(alertId: string): Promise<Alert> {
    return api.patch<Alert>(`/api/v1/alerts/${alertId}`, { read: true });
  },

  markActioned(alertId: string): Promise<Alert> {
    return api.patch<Alert>(`/api/v1/alerts/${alertId}`, { actioned: true, read: true });
  },

  markAllRead(): Promise<void> {
    return api.post<void>("/api/v1/alerts/mark-all-read");
  },

  snooze(alertId: string, hours: number): Promise<Alert> {
    return api.post<Alert>(`/api/v1/alerts/${alertId}/snooze`, { hours });
  },
};

// ─── Spend / Billing ────────────────────────────────────────────────────────

export const spendApi = {
  getSummary(period?: "day" | "week" | "month"): Promise<SpendSummary> {
    const query = qs({ period });
    return api.get<SpendSummary>(`/api/v1/billing/spend${query}`);
  },

  getRecords(params?: {
    page?: number;
    page_size?: number;
    member_id?: string;
    provider?: string;
  }): Promise<PaginatedResponse<SpendRecord>> {
    const query = qs({
      page: params?.page,
      page_size: params?.page_size,
      member_id: params?.member_id,
      provider: params?.provider,
    });
    return api.get<PaginatedResponse<SpendRecord>>(`/api/v1/billing/spend/records${query}`);
  },
  getThresholds(): Promise<BudgetThreshold[]> {
    return api.get<BudgetThreshold[]>("/api/v1/billing/thresholds");
  },

  createThreshold(data: {
    group_id: string;
    member_id?: string | null;
    type: "soft" | "hard";
    amount: number;
    notify_at?: number[];
  }): Promise<BudgetThreshold> {
    return api.post<BudgetThreshold>("/api/v1/billing/thresholds", data);
  },
};

// ─── Reports ────────────────────────────────────────────────────────────────

export const reportsApi = {
  list(params?: {
    page?: number;
    page_size?: number;
    type?: string;
    status?: string;
  }): Promise<PaginatedResponse<Report>> {
    const query = qs({
      page: params?.page,
      page_size: params?.page_size,
      type: params?.type,
      status: params?.status,
    });
    return api.get<PaginatedResponse<Report>>(`/api/v1/reports${query}`);
  },

  create(data: CreateReportRequest): Promise<Report> {
    return api.post<Report>("/api/v1/reports", data);
  },

  download(reportId: string): Promise<Blob> {
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    return fetch(`${BASE_URL}/api/v1/reports/${reportId}/download`, {
      headers,
      credentials: "include",
    }).then((res) => {
      if (!res.ok) throw new ApiRequestError(res.status, "Failed to download report");
      return res.blob();
    });
  },

  getSchedules(): Promise<ReportScheduleConfig[]> {
    return api.get<ReportScheduleConfig[]>("/api/v1/reports/schedules");
  },

  updateSchedule(data: ReportScheduleConfig): Promise<ReportScheduleConfig> {
    return api.put<ReportScheduleConfig>("/api/v1/reports/schedules", data);
  },
};

// ─── API Keys ────────────────────────────────────────────────────────────────

export const apiKeysApi = {
  list(): Promise<ApiKeyItem[]> {
    return api.get<ApiKeyItem[]>("/api/v1/auth/api-keys");
  },

  generate(data: CreateApiKeyRequest): Promise<CreateApiKeyResponse> {
    return api.post<CreateApiKeyResponse>("/api/v1/auth/api-keys", data);
  },

  revoke(keyId: string): Promise<void> {
    return api.delete<void>(`/api/v1/auth/api-keys/${keyId}`);
  },
};

// ─── Billing Checkout ────────────────────────────────────────────────────────

export const billingApi = {
  getTrialStatus(): Promise<TrialStatus> {
    return api.get<TrialStatus>("/api/v1/billing/trial-status");
  },

  createCheckout(data: CheckoutRequest): Promise<CheckoutResponse> {
    return api.post<CheckoutResponse>("/api/v1/billing/checkout", data);
  },

  getPortalUrl(): Promise<PortalResponse> {
    return api.get<PortalResponse>("/api/v1/billing/portal");
  },

  getSubscription(): Promise<SubscriptionStatus> {
    return api.get<SubscriptionStatus>("/api/v1/billing/subscription");
  },

  getPlans(): Promise<PlansResponse> {
    return api.get<PlansResponse>("/api/v1/billing/plans");
  },
};

// ─── Contact Inquiry ─────────────────────────────────────────────────────

export const contactApi = {
  submitInquiry(data: ContactInquiryRequest): Promise<{ message: string }> {
    return api.post<{ message: string }>("/api/v1/auth/contact-inquiry", data);
  },
};

// ─── Settings ───────────────────────────────────────────────────────────────

export const settingsApi = {
  getGroupSettings(): Promise<GroupSettings> {
    return api.get<GroupSettings>("/api/v1/portal/settings");
  },

  updateGroupSettings(data: UpdateGroupSettingsRequest): Promise<GroupSettings> {
    return api.patch<GroupSettings>("/api/v1/portal/settings", data);
  },

  updateProfile(data: UpdateProfileRequest): Promise<User> {
    return api.patch<User>("/api/v1/auth/me", data);
  },
};

// ─── Blocking ────────────────────────────────────────────────────────────────

export const blockingApi = {
  list(groupId: string): Promise<BlockRule[]> {
    return api.get<BlockRule[]>(`/api/v1/blocking/rules${qs({ group_id: groupId })}`);
  },

  check(groupId: string, memberId: string): Promise<BlockStatus> {
    return api.get<BlockStatus>(`/api/v1/blocking/check/${memberId}${qs({ group_id: groupId })}`);
  },

  create(data: { group_id: string; member_id: string; platforms?: string[]; reason?: string }): Promise<BlockRule> {
    return api.post<BlockRule>("/api/v1/blocking/rules", data);
  },

  revoke(ruleId: string): Promise<BlockRule> {
    return api.delete<BlockRule>(`/api/v1/blocking/rules/${ruleId}`);
  },

  requestUnblock(data: { group_id: string; block_rule_id: string; member_id: string; reason: string }): Promise<BlockApproval> {
    return api.post<BlockApproval>("/api/v1/blocking/approval-request", data);
  },

  approveUnblock(approvalId: string, data?: { decision_note?: string }): Promise<BlockApproval> {
    return api.post<BlockApproval>(`/api/v1/blocking/approve/${approvalId}`, data || {});
  },

  denyUnblock(approvalId: string, data?: { decision_note?: string }): Promise<BlockApproval> {
    return api.post<BlockApproval>(`/api/v1/blocking/deny/${approvalId}`, data || {});
  },

  pendingApprovals(groupId: string): Promise<BlockApproval[]> {
    return api.get<BlockApproval[]>(`/api/v1/blocking/pending-approvals${qs({ group_id: groupId })}`);
  },

  effectiveness(groupId: string): Promise<BlockEffectiveness> {
    return api.get<BlockEffectiveness>(`/api/v1/blocking/effectiveness${qs({ group_id: groupId })}`);
  },
};

// ─── Analytics ───────────────────────────────────────────────────────────────

export const analyticsApi = {
  trends(groupId: string, days?: number): Promise<TrendData> {
    return api.get<TrendData>(`/api/v1/analytics/trends${qs({ group_id: groupId, days: days || 7 })}`);
  },

  usagePatterns(groupId: string, days?: number): Promise<UsagePattern> {
    return api.get<UsagePattern>(`/api/v1/analytics/usage-patterns${qs({ group_id: groupId, days: days || 7 })}`);
  },

  memberBaselines(groupId: string, days?: number): Promise<MemberBaseline[]> {
    return api.get<MemberBaseline[]>(`/api/v1/analytics/member-baselines${qs({ group_id: groupId, days: days || 30 })}`);
  },

  anomalies(groupId: string, thresholdSd?: number): Promise<AnomalyResponse> {
    return api.get<AnomalyResponse>(`/api/v1/analytics/anomalies${qs({ group_id: groupId, threshold_sd: thresholdSd || 2.0 })}`);
  },

  peerComparison(groupId: string, days?: number): Promise<PeerComparisonResponse> {
    return api.get<PeerComparisonResponse>(`/api/v1/analytics/peer-comparison${qs({ group_id: groupId, days: days || 30 })}`);
  },

  academicReport(groupId: string, memberId: string, startDate?: string, endDate?: string): Promise<AcademicReport> {
    return api.get<AcademicReport>(`/api/v1/analytics/academic${qs({ group_id: groupId, member_id: memberId, start_date: startDate, end_date: endDate })}`);
  },

  classifyIntent(text: string): Promise<IntentClassification> {
    return api.get<IntentClassification>(`/api/v1/analytics/academic/intent${qs({ text })}`);
  },
};

// ─── Compliance (Phase 8) ────────────────────────────────────────────────────

export const complianceApi = {
  transparency(groupId: string): Promise<TransparencyReport> {
    return api.get<TransparencyReport>(`/api/v1/compliance/algorithmic-transparency${qs({ group_id: groupId })}`);
  },

  listAppeals(groupId: string): Promise<{ items: AppealRecord[]; total: number }> {
    return api.get<{ items: AppealRecord[]; total: number }>(`/api/v1/compliance/appeals${qs({ group_id: groupId })}`);
  },

  submitAppeal(riskEventId: string, data: { group_id: string; reason: string }): Promise<AppealRecord> {
    return api.post<AppealRecord>(`/api/v1/compliance/appeal/${riskEventId}`, data);
  },
};

// ─── Platform Safety (public) ────────────────────────────────────────────────

export const platformSafetyApi = {
  getAll(): Promise<{ platforms: PlatformSafetyRating[] }> {
    return api.get<{ platforms: PlatformSafetyRating[] }>("/api/v1/billing/platform-safety");
  },

  getOne(platform: string): Promise<PlatformSafetyRating> {
    return api.get<PlatformSafetyRating>(`/api/v1/billing/platform-safety/${platform}`);
  },

  getRecommendations(age: number): Promise<{ platforms: PlatformSafetyRecommendation[] }> {
    return api.get<{ platforms: PlatformSafetyRecommendation[] }>(
      `/api/v1/billing/platform-safety/recommend?age=${age}`
    );
  },
};

// ─── Summaries ──────────────────────────────────────────────────────────────

export const summariesApi = {
  list(params?: {
    member_id?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<ConversationSummary>> {
    const query = qs({
      member_id: params?.member_id,
      start_date: params?.start_date,
      end_date: params?.end_date,
      page: params?.page,
      page_size: params?.page_size,
    });
    return api.get<PaginatedResponse<ConversationSummary>>(`/api/v1/capture/summaries${query}`);
  },

  get(summaryId: string): Promise<ConversationSummary> {
    return api.get<ConversationSummary>(`/api/v1/capture/summaries/${summaryId}`);
  },

  summarize(data: { event_id: string; member_age?: number }): Promise<ConversationSummary> {
    return api.post<ConversationSummary>("/api/v1/capture/summarize", data);
  },
};

// ─── Family Agreement ────────────────────────────────────────────────────────

export const agreementApi = {
  getTemplates(): Promise<Record<string, { title: string; rules: { category: string; text: string }[] }>> {
    return api.get("/api/v1/groups/agreement-templates");
  },

  getActive(groupId: string) {
    return api.get(`/api/v1/groups/${groupId}/agreement`);
  },

  create(groupId: string, data: { template_id: string }) {
    return api.post(`/api/v1/groups/${groupId}/agreement`, data);
  },

  update(groupId: string, data: { rules: unknown[] }) {
    return api.patch(`/api/v1/groups/${groupId}/agreement`, data);
  },

  sign(groupId: string, data: { member_id: string; name: string }) {
    return api.post(`/api/v1/groups/${groupId}/agreement/sign`, data);
  },

  review(groupId: string) {
    return api.post(`/api/v1/groups/${groupId}/agreement/review`);
  },
};

// ─── Emergency Contacts ──────────────────────────────────────────────────────

export const emergencyContactsApi = {
  list(groupId: string) {
    return api.get(`/api/v1/groups/${groupId}/emergency-contacts`);
  },

  add(groupId: string, data: unknown) {
    return api.post(`/api/v1/groups/${groupId}/emergency-contacts`, data);
  },

  update(groupId: string, contactId: string, data: unknown) {
    return api.patch(`/api/v1/groups/${groupId}/emergency-contacts/${contactId}`, data);
  },

  remove(groupId: string, contactId: string) {
    return api.delete(`/api/v1/groups/${groupId}/emergency-contacts/${contactId}`);
  },
};

// ─── Family Weekly Report ────────────────────────────────────────────────────

export const familyReportApi = {
  getWeekly() {
    return api.get("/api/v1/reports/weekly-family");
  },

  send() {
    return api.post("/api/v1/reports/weekly-family/send");
  },
};

// ─── Privacy (F11) ──────────────────────────────────────────────────────────

export const privacyApi = {
  getVisibility(groupId: string, memberId: string): Promise<MemberVisibility> {
    return api.get<MemberVisibility>(`/api/v1/groups/${groupId}/members/${memberId}/visibility`);
  },

  setVisibility(groupId: string, memberId: string, data: SetVisibilityRequest): Promise<MemberVisibility> {
    return api.put<MemberVisibility>(`/api/v1/groups/${groupId}/members/${memberId}/visibility`, data);
  },

  getSelfView(groupId: string, memberId: string): Promise<ChildSelfView> {
    return api.get<ChildSelfView>(`/api/v1/groups/${groupId}/members/${memberId}/self-view`);
  },

  setSelfView(groupId: string, memberId: string, data: SetChildSelfViewRequest): Promise<ChildSelfView> {
    return api.put<ChildSelfView>(`/api/v1/groups/${groupId}/members/${memberId}/self-view`, data);
  },

  getChildDashboard(memberId: string): Promise<ChildDashboard> {
    return api.get<ChildDashboard>(`/api/v1/portal/child-dashboard${qs({ member_id: memberId })}`);
  },
};

// ─── Device Correlation (F12) ───────────────────────────────────────────────

export const deviceApi = {
  getSessionSummary(memberId: string, date?: string): Promise<DeviceSessionSummary> {
    return api.get<DeviceSessionSummary>(`/api/v1/capture/devices/${memberId}/summary${qs({ target_date: date })}`);
  },
};

// ─── Rewards (F14) ──────────────────────────────────────────────────────────

export const rewardsApi = {
  list(groupId: string, memberId: string): Promise<RewardItem[]> {
    return api.get<RewardItem[]>(`/api/v1/groups/${groupId}/members/${memberId}/rewards`);
  },

  checkTriggers(groupId: string, memberId: string): Promise<RewardItem[]> {
    return api.post<RewardItem[]>(`/api/v1/groups/${groupId}/members/${memberId}/rewards/check`);
  },
};

// ─── Integrations ────────────────────────────────────────────────────────────

export const integrationsApi = {
  listConnections(groupId: string): Promise<SISConnection[]> {
    return api.get<SISConnection[]>(`/api/v1/integrations/status${qs({ group_id: groupId })}`);
  },

  connect(data: { group_id: string; provider: string; access_token: string }): Promise<SISConnection> {
    return api.post<SISConnection>("/api/v1/integrations/connect", data);
  },

  sync(connectionId: string): Promise<{ members_created: number; members_updated: number }> {
    return api.post<{ members_created: number; members_updated: number }>(`/api/v1/integrations/sync/${connectionId}`);
  },

  disconnect(connectionId: string): Promise<void> {
    return api.delete<void>(`/api/v1/integrations/disconnect/${connectionId}`);
  },

  startAgeVerification(groupId: string, memberId: string): Promise<{ session_url: string }> {
    return api.post<{ session_url: string }>(`/api/v1/integrations/age-verify/start${qs({ group_id: groupId, member_id: memberId })}`);
  },

  listSSOConfigs(groupId: string): Promise<SSOConfig[]> {
    return api.get<SSOConfig[]>(`/api/v1/integrations/sso${qs({ group_id: groupId })}`);
  },

  updateSSOConfig(configId: string, data: { auto_provision_members?: boolean; tenant_id?: string }): Promise<SSOConfig> {
    return api.patch<SSOConfig>(`/api/v1/integrations/sso/${configId}`, data);
  },

  triggerDirectorySync(configId: string): Promise<{ synced: number; skipped: number; errors: number }> {
    return api.post<{ synced: number; skipped: number; errors: number }>(`/api/v1/integrations/sso/${configId}/sync`);
  },
};
