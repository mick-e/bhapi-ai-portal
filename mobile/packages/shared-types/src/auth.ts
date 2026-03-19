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
