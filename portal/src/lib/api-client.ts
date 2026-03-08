import type {
  ApiError,
  ApiKeyItem,
  AppealRecord,
  BlockRule,
  BlockStatus,
  CheckoutRequest,
  CheckoutResponse,
  ContactInquiryRequest,
  CreateApiKeyRequest,
  CreateApiKeyResponse,
  CreateGroupRequest,
  DashboardData,
  Group,
  GroupMember,
  InviteMemberRequest,
  UpdateMemberRequest,
  CaptureEvent,
  MemberBaseline,
  RiskEvent,
  AcknowledgeRiskRequest,
  Alert,
  SISConnection,
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
  UsagePattern,
  User,
  BudgetThreshold,
  ConsentRecord,
  RecordConsentRequest,
  PaginatedResponse,
  PortalResponse,
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
      const errorBody: ApiError = await response.json();
      detail = errorBody.detail || detail;
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

interface RiskEventListBackend {
  items: RiskEvent[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

export const riskApi = {
  async list(params?: {
    page?: number;
    page_size?: number;
    severity?: string;
    category?: string;
    resolved?: boolean;
    member_id?: string;
  }): Promise<PaginatedResponse<RiskEvent>> {
    const page = params?.page ?? 1;
    const pageSize = params?.page_size ?? 20;
    const offset = (page - 1) * pageSize;
    const query = qs({
      offset,
      limit: pageSize,
      severity: params?.severity,
      category: params?.category,
      acknowledged: params?.resolved,
      member_id: params?.member_id,
    });
    const data = await api.get<RiskEventListBackend>(`/api/v1/risk/events${query}`);
    return {
      items: data.items,
      total: data.total,
      page,
      page_size: pageSize,
      total_pages: Math.max(1, Math.ceil(data.total / pageSize)),
    };
  },

  acknowledge(data: AcknowledgeRiskRequest): Promise<RiskEvent> {
    return api.post<RiskEvent>(`/api/v1/risk/events/${data.event_id}/acknowledge`, data);
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
  createCheckout(data: CheckoutRequest): Promise<CheckoutResponse> {
    return api.post<CheckoutResponse>("/api/v1/billing/checkout", data);
  },

  getPortalUrl(): Promise<PortalResponse> {
    return api.get<PortalResponse>("/api/v1/billing/portal");
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
};
