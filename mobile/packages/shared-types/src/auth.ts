export interface User {
  id: string;
  email: string;
  role: 'parent' | 'child' | 'school_admin' | 'moderator' | 'support' | 'super_admin';
  group_id: string | null;
  email_verified: boolean;
  created_at: string;
}

export interface AuthTokenPayload {
  user_id: string;
  group_id: string | null;
  role: string;
  permissions: string[];
  type: 'session';
  exp: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: 'bearer';
  user: User;
}

// ---------------------------------------------------------------------------
// Consent
// ---------------------------------------------------------------------------

export type ConsentType = 'social_access' | 'data_processing' | 'third_party';

export interface ConsentRecord {
  id: string;
  user_id: string;
  consent_type: ConsentType;
  granted: boolean;
  granted_by: string | null;
  granted_at: string | null;
  expires_at: string | null;
}

export interface ParentConsentStatus {
  child_user_id: string;
  consent_type: ConsentType;
  status: 'pending' | 'granted' | 'denied' | 'expired';
  parent_email: string | null;
  requested_at: string;
}
