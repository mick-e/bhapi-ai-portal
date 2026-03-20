/**
 * REST API client for Bhapi backend.
 * Features: auth header injection, retry with exponential backoff, offline queue integration.
 */

import { OfflineQueue } from './offline-queue';

export interface ApiClientConfig {
  baseUrl: string;
  getToken: () => Promise<string | null>;
  /** Max retry attempts for retriable errors (default: 3) */
  maxRetries?: number;
  /** Base delay for exponential backoff in ms (default: 1000) */
  retryBaseDelay?: number;
  /** Optional offline queue for queueing requests when offline */
  offlineQueue?: OfflineQueue;
  /** Function to check if device is online (default: true) */
  isOnline?: () => boolean;
}

/** HTTP status codes that are safe to retry */
const RETRIABLE_STATUS_CODES = new Set([408, 429, 500, 502, 503, 504]);

export class ApiClient {
  private config: ApiClientConfig;
  private maxRetries: number;
  private retryBaseDelay: number;

  constructor(config: ApiClientConfig) {
    this.config = config;
    this.maxRetries = config.maxRetries ?? 3;
    this.retryBaseDelay = config.retryBaseDelay ?? 1000;
  }

  async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    // Check offline status and queue if applicable
    if (this.config.offlineQueue && this.config.isOnline && !this.config.isOnline()) {
      if (method !== 'GET') {
        this.config.offlineQueue.enqueue({ method, path, body });
        throw new ApiError(0, 'OFFLINE', 'Request queued for offline replay');
      }
      throw new ApiError(0, 'OFFLINE', 'Device is offline');
    }

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        return await this.executeRequest<T>(method, path, body);
      } catch (e) {
        lastError = e as Error;

        // Only retry on retriable errors
        if (e instanceof ApiError && !RETRIABLE_STATUS_CODES.has(e.status)) {
          throw e;
        }

        // Network errors are retriable
        if (!(e instanceof ApiError) && !(e instanceof TypeError)) {
          throw e;
        }

        // Don't retry on last attempt
        if (attempt < this.maxRetries) {
          const delay = this.retryBaseDelay * Math.pow(2, attempt);
          await this.sleep(delay);
        }
      }
    }

    throw lastError!;
  }

  private async executeRequest<T>(method: string, path: string, body?: unknown): Promise<T> {
    const token = await this.config.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.config.baseUrl}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        error: response.statusText,
        code: `HTTP_${response.status}`,
      }));
      throw new ApiError(response.status, error.code, error.error);
    }

    return response.json();
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path);
  }

  post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>('POST', path, body);
  }

  put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>('PUT', path, body);
  }

  delete<T>(path: string): Promise<T> {
    return this.request<T>('DELETE', path);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
