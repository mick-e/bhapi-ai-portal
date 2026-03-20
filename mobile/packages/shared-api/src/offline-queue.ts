/**
 * Offline request queue.
 * Queues API requests when offline and replays them on reconnect.
 */

export interface QueuedRequest {
  id: string;
  method: string;
  path: string;
  body?: unknown;
  timestamp: number;
}

export interface ReplayResult {
  succeeded: number;
  failed: number;
  errors: Array<{ id: string; error: string }>;
}

/** Minimal API client interface for replay */
export interface ReplayClient {
  request<T>(method: string, path: string, body?: unknown): Promise<T>;
}

export class OfflineQueue {
  private queue: QueuedRequest[] = [];
  private maxSize: number;
  private maxAgeMs: number;
  private _isReplaying = false;

  constructor(options?: { maxSize?: number; maxAgeMs?: number }) {
    this.maxSize = options?.maxSize ?? 100;
    this.maxAgeMs = options?.maxAgeMs ?? 24 * 60 * 60 * 1000; // 24 hours
  }

  /**
   * Add a request to the queue.
   * Drops oldest entries if queue exceeds maxSize.
   */
  enqueue(request: Omit<QueuedRequest, 'id' | 'timestamp'>): string {
    const id = this.generateId();
    const entry: QueuedRequest = {
      ...request,
      id,
      timestamp: Date.now(),
    };

    this.queue.push(entry);

    // Evict oldest if over capacity
    while (this.queue.length > this.maxSize) {
      this.queue.shift();
    }

    return id;
  }

  /**
   * Replay all queued requests through the given client.
   * Removes successfully replayed requests.
   * Stale requests (older than maxAgeMs) are dropped without replay.
   */
  async replay(client: ReplayClient): Promise<ReplayResult> {
    if (this._isReplaying) {
      return { succeeded: 0, failed: 0, errors: [] };
    }

    this._isReplaying = true;
    const result: ReplayResult = { succeeded: 0, failed: 0, errors: [] };
    const now = Date.now();

    // Remove stale requests
    const validQueue = this.queue.filter((r) => now - r.timestamp < this.maxAgeMs);
    const staleCount = this.queue.length - validQueue.length;
    result.failed += staleCount;

    const remaining: QueuedRequest[] = [];

    for (const request of validQueue) {
      try {
        await client.request(request.method, request.path, request.body);
        result.succeeded++;
      } catch (e: any) {
        result.failed++;
        result.errors.push({
          id: request.id,
          error: e?.message || 'Unknown error',
        });
        // Keep failed requests for retry (unless stale)
        remaining.push(request);
      }
    }

    this.queue = remaining;
    this._isReplaying = false;

    return result;
  }

  /**
   * Get the current number of queued requests.
   */
  getSize(): number {
    return this.queue.length;
  }

  /**
   * Clear all queued requests.
   */
  clear(): void {
    this.queue = [];
  }

  /**
   * Get a copy of the current queue.
   */
  getQueue(): ReadonlyArray<QueuedRequest> {
    return [...this.queue];
  }

  /**
   * Remove a specific request by ID.
   */
  remove(id: string): boolean {
    const index = this.queue.findIndex((r) => r.id === id);
    if (index === -1) return false;
    this.queue.splice(index, 1);
    return true;
  }

  /**
   * Whether the queue is currently replaying.
   */
  get isReplaying(): boolean {
    return this._isReplaying;
  }

  private generateId(): string {
    return `q_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  }
}
