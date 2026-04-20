/**
 * WebSocket client for real-time service.
 * Supports auto-reconnect with exponential backoff.
 */

export type WebSocketEventType =
  | 'open'
  | 'close'
  | 'error'
  | 'message'
  | 'new_message'
  | 'typing_start'
  | 'typing_stop'
  | 'read_receipt';

export interface WebSocketMessage {
  type: string;
  data: unknown;
  timestamp?: number;
}

export interface NewMessageEvent {
  message_id: string;
  conversation_id: string;
  sender_id: string;
  content: string;
  message_type: string;
  created_at: string;
}

export interface TypingEvent {
  user_id: string;
  conversation_id: string;
}

export interface ReadReceiptEvent {
  user_id: string;
  conversation_id: string;
  read_at: string;
}

type EventCallback = (data: any) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts: number;
  private baseDelay: number;
  private maxDelay: number;
  private listeners = new Map<string, Set<EventCallback>>();
  private url: string | null = null;
  private token: string | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _connected = false;
  private _shouldReconnect = true;

  constructor(options?: {
    maxReconnectAttempts?: number;
    baseDelay?: number;
    maxDelay?: number;
  }) {
    this.maxReconnectAttempts = options?.maxReconnectAttempts ?? 5;
    this.baseDelay = options?.baseDelay ?? 1000;
    // Cap exponential growth so attempt #20 doesn't schedule a 12-day retry.
    // Default 60s matches typical server restart windows; with ±20% jitter
    // this also prevents reconnection thundering herds on server bounce.
    this.maxDelay = options?.maxDelay ?? 60_000;
  }

  /**
   * Connect to a WebSocket server.
   */
  connect(url: string, token: string): void {
    this.url = url;
    this.token = token;
    this._shouldReconnect = true;
    this.reconnectAttempts = 0;
    this.createConnection();
  }

  /**
   * Disconnect and stop reconnection attempts.
   */
  disconnect(): void {
    this._shouldReconnect = false;
    this.clearReconnectTimer();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._connected = false;
  }

  /**
   * Send a typed message over the WebSocket.
   */
  send(type: string, data: unknown): void {
    if (!this.ws || !this._connected) {
      throw new Error('WebSocket is not connected');
    }

    const message: WebSocketMessage = {
      type,
      data,
      timestamp: Date.now(),
    };

    this.ws.send(JSON.stringify(message));
  }

  /**
   * Register an event listener.
   * Supports: 'open', 'close', 'error', 'message', or custom message types.
   */
  on(event: string, callback: EventCallback): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  /**
   * Remove an event listener.
   */
  off(event: string, callback: EventCallback): void {
    this.listeners.get(event)?.delete(callback);
  }

  /**
   * Send a typing start indicator for a conversation.
   */
  sendTypingStart(conversationId: string): void {
    this.send('typing_start', { conversation_id: conversationId });
  }

  /**
   * Send a typing stop indicator for a conversation.
   */
  sendTypingStop(conversationId: string): void {
    this.send('typing_stop', { conversation_id: conversationId });
  }

  /**
   * Send a read receipt for a conversation.
   */
  sendReadReceipt(conversationId: string): void {
    this.send('read_receipt', {
      conversation_id: conversationId,
      read_at: new Date().toISOString(),
    });
  }

  /**
   * Join a conversation room to receive real-time messages.
   */
  joinConversation(conversationId: string): void {
    this.send('join_room', { room: `conversation:${conversationId}` });
  }

  /**
   * Leave a conversation room.
   */
  leaveConversation(conversationId: string): void {
    this.send('leave_room', { room: `conversation:${conversationId}` });
  }

  /**
   * Whether the client is currently connected.
   */
  get isConnected(): boolean {
    return this._connected;
  }

  /**
   * Current reconnect attempt count.
   */
  get attempts(): number {
    return this.reconnectAttempts;
  }

  private createConnection(): void {
    if (!this.url) return;

    const wsUrl = this.token
      ? `${this.url}?token=${encodeURIComponent(this.token)}`
      : this.url;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this._connected = true;
      this.reconnectAttempts = 0;
      this.emit('open', undefined);
    };

    this.ws.onclose = (event) => {
      this._connected = false;
      this.emit('close', { code: event.code, reason: event.reason });
      this.attemptReconnect();
    };

    this.ws.onerror = (event) => {
      this.emit('error', event);
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.emit('message', message);
        // Also emit by message type for typed listeners
        if (message.type) {
          this.emit(message.type, message.data);
        }
      } catch {
        // Non-JSON message, emit raw
        this.emit('message', { type: 'raw', data: event.data });
      }
    };
  }

  private attemptReconnect(): void {
    if (!this._shouldReconnect) return;
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.emit('error', { message: 'Max reconnection attempts reached' });
      return;
    }

    // Exponential backoff capped at maxDelay, with ±20% jitter to
    // spread reconnects across clients on server restart.
    const raw = this.baseDelay * Math.pow(2, this.reconnectAttempts);
    const capped = Math.min(raw, this.maxDelay);
    const jitter = capped * (0.8 + Math.random() * 0.4);
    this.reconnectAttempts++;

    this.reconnectTimer = setTimeout(() => {
      this.createConnection();
    }, jitter);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private emit(event: string, data: any): void {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach((cb) => cb(data));
    }
  }
}
