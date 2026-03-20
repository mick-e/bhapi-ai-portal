/**
 * Offline event cache for Chromebook deployment.
 * Stores capture events in IndexedDB when offline, replays on reconnect.
 *
 * Designed for school Chromebooks where network connectivity may be
 * intermittent. Events are persisted locally and automatically synced
 * when the device comes back online.
 */

import { CaptureEvent } from "./shared/types";

const DB_NAME = "bhapi-offline-cache";
const DB_VERSION = 1;
const STORE_NAME = "events";
const MAX_EVENTS = 1000;
const MAX_RETRIES = 5;

export interface CachedEvent {
  id: string;
  event: CaptureEvent;
  timestamp: number;
  retryCount: number;
}

export interface SyncResult {
  synced: number;
  failed: number;
}

/**
 * Generate a unique ID for cached events.
 * Uses crypto.randomUUID when available, falls back to timestamp + random.
 */
function generateId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

export class OfflineCache {
  private db: IDBDatabase | null = null;

  /**
   * Open (or create) the IndexedDB database.
   */
  async init(): Promise<void> {
    if (this.db) return;

    return new Promise<void>((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: "id" });
          store.createIndex("timestamp", "timestamp", { unique: false });
        }
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onerror = () => {
        reject(new Error(`Failed to open IndexedDB: ${request.error?.message}`));
      };
    });
  }

  /**
   * Ensure the database is initialized before any operation.
   */
  private async ensureDb(): Promise<IDBDatabase> {
    if (!this.db) {
      await this.init();
    }
    if (!this.db) {
      throw new Error("IndexedDB not available");
    }
    return this.db;
  }

  /**
   * Add a capture event to the offline cache.
   * Enforces MAX_EVENTS with FIFO eviction — oldest events are removed first.
   */
  async addEvent(event: CaptureEvent): Promise<string> {
    const db = await this.ensureDb();
    const id = generateId();

    const cachedEvent: CachedEvent = {
      id,
      event,
      timestamp: Date.now(),
      retryCount: 0,
    };

    // Enforce max events by evicting oldest first
    const count = await this.getCount();
    if (count >= MAX_EVENTS) {
      const evictCount = count - MAX_EVENTS + 1;
      await this.evictOldest(evictCount);
    }

    return new Promise<string>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const request = store.add(cachedEvent);

      request.onsuccess = () => resolve(id);
      request.onerror = () => reject(new Error(`Failed to add event: ${request.error?.message}`));
    });
  }

  /**
   * Get all cached events ordered by timestamp (oldest first).
   */
  async getEvents(): Promise<CachedEvent[]> {
    const db = await this.ensureDb();

    return new Promise<CachedEvent[]>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const index = store.index("timestamp");
      const request = index.getAll();

      request.onsuccess = () => resolve(request.result as CachedEvent[]);
      request.onerror = () => reject(new Error(`Failed to get events: ${request.error?.message}`));
    });
  }

  /**
   * Remove a single event by ID (after successful sync).
   */
  async removeEvent(id: string): Promise<void> {
    const db = await this.ensureDb();

    return new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const request = store.delete(id);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(new Error(`Failed to remove event: ${request.error?.message}`));
    });
  }

  /**
   * Get the number of cached events.
   */
  async getCount(): Promise<number> {
    const db = await this.ensureDb();

    return new Promise<number>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const request = store.count();

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(new Error(`Failed to count events: ${request.error?.message}`));
    });
  }

  /**
   * Clear all cached events.
   */
  async clear(): Promise<void> {
    const db = await this.ensureDb();

    return new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const request = store.clear();

      request.onsuccess = () => resolve();
      request.onerror = () => reject(new Error(`Failed to clear events: ${request.error?.message}`));
    });
  }

  /**
   * Replay cached events to the API endpoint.
   * Events are sent oldest-first. Successfully synced events are removed.
   * Failed events have their retryCount incremented; events exceeding
   * MAX_RETRIES are discarded.
   */
  async syncEvents(apiEndpoint: string, authToken: string): Promise<SyncResult> {
    const events = await this.getEvents();
    let synced = 0;
    let failed = 0;

    for (const cached of events) {
      // Discard events that have exceeded retry limit
      if (cached.retryCount >= MAX_RETRIES) {
        await this.removeEvent(cached.id);
        failed++;
        continue;
      }

      try {
        const response = await fetch(`${apiEndpoint}/api/v1/capture/events`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${authToken}`,
          },
          body: JSON.stringify(cached.event),
        });

        if (response.ok) {
          await this.removeEvent(cached.id);
          synced++;
        } else {
          await this.incrementRetry(cached.id);
          failed++;
        }
      } catch {
        await this.incrementRetry(cached.id);
        failed++;
      }
    }

    return { synced, failed };
  }

  /**
   * Get a single cached event by ID.
   */
  async getEvent(id: string): Promise<CachedEvent | undefined> {
    const db = await this.ensureDb();

    return new Promise<CachedEvent | undefined>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const request = store.get(id);

      request.onsuccess = () => resolve(request.result as CachedEvent | undefined);
      request.onerror = () => reject(new Error(`Failed to get event: ${request.error?.message}`));
    });
  }

  /**
   * Evict the N oldest events from the cache.
   */
  private async evictOldest(count: number): Promise<void> {
    const db = await this.ensureDb();

    return new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const index = store.index("timestamp");
      const request = index.openCursor();
      let evicted = 0;

      request.onsuccess = () => {
        const cursor = request.result;
        if (cursor && evicted < count) {
          cursor.delete();
          evicted++;
          cursor.continue();
        } else {
          resolve();
        }
      };

      request.onerror = () => reject(new Error(`Failed to evict events: ${request.error?.message}`));
    });
  }

  /**
   * Increment the retry count for a cached event.
   */
  private async incrementRetry(id: string): Promise<void> {
    const db = await this.ensureDb();

    return new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const getReq = store.get(id);

      getReq.onsuccess = () => {
        const cached = getReq.result as CachedEvent | undefined;
        if (cached) {
          cached.retryCount++;
          const putReq = store.put(cached);
          putReq.onsuccess = () => resolve();
          putReq.onerror = () => reject(new Error(`Failed to update retry count: ${putReq.error?.message}`));
        } else {
          resolve();
        }
      };

      getReq.onerror = () => reject(new Error(`Failed to get event for retry: ${getReq.error?.message}`));
    });
  }

  /**
   * Close the database connection.
   */
  close(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }
}

/** Singleton instance for use across the extension. */
export const offlineCache = new OfflineCache();
