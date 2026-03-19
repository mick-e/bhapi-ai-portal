/**
 * Token manager for JWT auth.
 * Phase 0 stub: uses in-memory storage for testing.
 * TODO Phase 1: Replace with expo-secure-store for SecureStore.
 * NOTE: atob() works in Node.js/Jest but needs a polyfill (base-64 or expo-crypto)
 * in the React Native runtime.
 */

let _accessToken: string | null = null;

export const tokenManager = {
  async getToken(): Promise<string | null> {
    return _accessToken;
  },

  async setToken(token: string): Promise<void> {
    _accessToken = token;
  },

  async clearToken(): Promise<void> {
    _accessToken = null;
  },

  async isAuthenticated(): Promise<boolean> {
    const token = await this.getToken();
    if (!token) return false;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  },
};
