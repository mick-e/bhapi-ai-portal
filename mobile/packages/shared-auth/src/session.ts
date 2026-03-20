/**
 * Session management with auto-refresh and expiry monitoring.
 */

import { tokenManager } from './token-manager';

export interface SessionConfig {
  /** Seconds before expiry to trigger refresh (default: 300 = 5 minutes) */
  refreshBeforeExpiry: number;
  /** Callback to refresh the token; returns new token or null on failure */
  onRefresh: () => Promise<string | null>;
  /** Callback when session expires */
  onExpired?: () => void;
  /** Polling interval in seconds for expiry check (default: 60) */
  checkIntervalSeconds: number;
}

const DEFAULT_CONFIG: SessionConfig = {
  refreshBeforeExpiry: 300,
  onRefresh: async () => null,
  checkIntervalSeconds: 60,
};

export class SessionManager {
  private refreshTimer: ReturnType<typeof setInterval> | null = null;
  private config: SessionConfig;
  private _isActive = false;
  private _tokenExp: number | null = null;

  constructor(config?: Partial<SessionConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Start a session with the given token.
   * Parses token expiry and begins auto-refresh monitoring.
   */
  async startSession(token: string): Promise<void> {
    await tokenManager.setToken(token);
    this._tokenExp = this.parseExp(token);
    this._isActive = true;
    this.startMonitoring();
  }

  /**
   * Attempt to refresh the current session.
   * Returns true if refresh succeeded.
   */
  async refreshSession(): Promise<boolean> {
    try {
      const newToken = await this.config.onRefresh();
      if (!newToken) {
        return false;
      }
      await tokenManager.setToken(newToken);
      this._tokenExp = this.parseExp(newToken);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * End the session: clear token and stop monitoring.
   */
  async endSession(): Promise<void> {
    this.stopMonitoring();
    await tokenManager.clearToken();
    this._isActive = false;
    this._tokenExp = null;
  }

  /**
   * Whether the session is currently active and not expired.
   */
  isSessionActive(): boolean {
    if (!this._isActive || this._tokenExp === null) return false;
    return this._tokenExp * 1000 > Date.now();
  }

  /**
   * Seconds until the token expires, or 0 if expired/no session.
   */
  getTimeUntilExpiry(): number {
    if (this._tokenExp === null) return 0;
    const remaining = this._tokenExp - Math.floor(Date.now() / 1000);
    return Math.max(0, remaining);
  }

  /**
   * Get the token expiry timestamp (Unix seconds) or null.
   */
  getExpiry(): number | null {
    return this._tokenExp;
  }

  private parseExp(token: string): number | null {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp ?? null;
    } catch {
      return null;
    }
  }

  private startMonitoring(): void {
    this.stopMonitoring();
    this.refreshTimer = setInterval(async () => {
      await this.checkAndRefresh();
    }, this.config.checkIntervalSeconds * 1000);
  }

  private stopMonitoring(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  private async checkAndRefresh(): Promise<void> {
    const remaining = this.getTimeUntilExpiry();

    if (remaining <= 0) {
      this._isActive = false;
      this.stopMonitoring();
      this.config.onExpired?.();
      return;
    }

    if (remaining <= this.config.refreshBeforeExpiry) {
      const success = await this.refreshSession();
      if (!success) {
        this._isActive = false;
        this.stopMonitoring();
        this.config.onExpired?.();
      }
    }
  }
}
