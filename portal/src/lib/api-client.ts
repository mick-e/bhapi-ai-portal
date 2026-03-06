import type {
  ApiError,
  ApiKeyItem,
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
  RiskEvent,
  AcknowledgeRiskRequest,
  Alert,
  SpendSummary,
  SpendRecord,
  Report,
  CreateReportRequest,
  ReportScheduleConfig,
  GroupSettings,
  UpdateGroupSettingsRequest,
  UpdateProfileRequest,
  User,
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
  }): Promise<PaginatedResponse<CaptureEvent>> {
    const query = qs({
      page: params?.page,
      page_size: params?.page_size,
      member_id: params?.member_id,
      risk_level: params?.risk_level,
      provider: params?.provider,
      event_type: params?.event_type,
      search: params?.search,
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
      resolved: params?.resolved,
      member_id: params?.member_id,
    });
    return api.get<PaginatedResponse<RiskEvent>>(`/api/v1/risk/events${query}`);
  },

  acknowledge(data: AcknowledgeRiskRequest): Promise<RiskEvent> {
    return api.post<RiskEvent>("/api/v1/risk/acknowledge", data);
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
  }): Promise<PaginatedResponse<Alert>> {
    const query = qs({
      page: params?.page,
      page_size: params?.page_size,
      severity: params?.severity,
      type: params?.type,
      read: params?.read,
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
