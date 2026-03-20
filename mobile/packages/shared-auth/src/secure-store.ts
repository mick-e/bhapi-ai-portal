/**
 * SecureStore adapter with in-memory fallback.
 * Uses expo-secure-store on native, falls back to in-memory for web/test.
 */

export interface SecureStoreAdapter {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  deleteItem(key: string): Promise<void>;
}

/**
 * In-memory fallback store for web/test environments.
 */
export class InMemoryStore implements SecureStoreAdapter {
  private store = new Map<string, string>();

  async getItem(key: string): Promise<string | null> {
    return this.store.get(key) ?? null;
  }

  async setItem(key: string, value: string): Promise<void> {
    if (!key) throw new Error('Key must not be empty');
    if (!value && value !== '') throw new Error('Value must be a string');
    this.store.set(key, value);
  }

  async deleteItem(key: string): Promise<void> {
    this.store.delete(key);
  }

  /** Test helper: clear all stored items */
  clear(): void {
    this.store.clear();
  }

  /** Test helper: get number of stored items */
  get size(): number {
    return this.store.size;
  }
}

/**
 * Expo SecureStore wrapper that conforms to the adapter interface.
 */
class ExpoSecureStoreAdapter implements SecureStoreAdapter {
  private expoStore: any;

  constructor(expoStore: any) {
    this.expoStore = expoStore;
  }

  async getItem(key: string): Promise<string | null> {
    return this.expoStore.getItemAsync(key);
  }

  async setItem(key: string, value: string): Promise<void> {
    await this.expoStore.setItemAsync(key, value);
  }

  async deleteItem(key: string): Promise<void> {
    await this.expoStore.deleteItemAsync(key);
  }
}

let _defaultStore: SecureStoreAdapter | null = null;

/**
 * Create a SecureStore adapter.
 * Attempts to use expo-secure-store; falls back to in-memory.
 */
export function createSecureStore(): SecureStoreAdapter {
  if (_defaultStore) return _defaultStore;

  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const ExpoSecureStore = require('expo-secure-store');
    _defaultStore = new ExpoSecureStoreAdapter(ExpoSecureStore);
  } catch {
    _defaultStore = new InMemoryStore();
  }

  return _defaultStore;
}

/**
 * Reset the default store (for testing).
 */
export function resetSecureStore(): void {
  _defaultStore = null;
}
