/**
 * Token manager for JWT auth.
 * Uses SecureStore adapter (expo-secure-store on native, in-memory fallback).
 */

import { createSecureStore, type SecureStoreAdapter } from './secure-store';

const TOKEN_KEY = 'bhapi_access_token';

let _store: SecureStoreAdapter | null = null;

function getStore(): SecureStoreAdapter {
  if (!_store) {
    _store = createSecureStore();
  }
  return _store;
}

export const tokenManager = {
  async getToken(): Promise<string | null> {
    return getStore().getItem(TOKEN_KEY);
  },

  async setToken(token: string): Promise<void> {
    await getStore().setItem(TOKEN_KEY, token);
  },

  async clearToken(): Promise<void> {
    await getStore().deleteItem(TOKEN_KEY);
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

  /**
   * Override the store instance (for testing).
   */
  _setStore(store: SecureStoreAdapter): void {
    _store = store;
  },

  /**
   * Reset to default store (for testing).
   */
  _resetStore(): void {
    _store = null;
  },
};
