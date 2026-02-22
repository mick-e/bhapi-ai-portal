/**
 * Bhapi AI Safety Monitor — Shared Types
 *
 * Core type definitions used across the extension:
 * background service worker, content scripts, and popup.
 */

// ---------------------------------------------------------------------------
// Platform identification
// ---------------------------------------------------------------------------

/** Supported AI platforms that the extension monitors. */
export type PlatformType = "chatgpt" | "gemini" | "copilot" | "claude" | "grok";

/** Human-readable display names keyed by PlatformType. */
export const PLATFORM_LABELS: Record<PlatformType, string> = {
  chatgpt: "ChatGPT",
  gemini: "Google Gemini",
  copilot: "Microsoft Copilot",
  claude: "Anthropic Claude",
  grok: "xAI Grok",
};

// ---------------------------------------------------------------------------
// Capture events
// ---------------------------------------------------------------------------

/** The types of events the extension can capture from AI platforms. */
export type EventType =
  | "prompt_submitted"
  | "response_received"
  | "session_started"
  | "session_ended"
  | "platform_detected"
  | "error";

/**
 * A single capture event sent from a content script to the background worker
 * and ultimately to the Bhapi capture gateway.
 */
export interface CaptureEvent {
  /** Organisation / team group identifier. */
  groupId: string;
  /** Individual member identifier within the group. */
  memberId: string;
  /** Which AI platform generated this event. */
  platform: PlatformType;
  /** Unique session identifier (generated per page load / conversation). */
  sessionId: string;
  /** What happened. */
  eventType: EventType;
  /** ISO-8601 timestamp of when the event occurred. */
  timestamp: string;
  /** Optional structured metadata (prompt length, response length, etc.). */
  metadata?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Extension configuration (persisted in chrome.storage.local)
// ---------------------------------------------------------------------------

/** Configuration stored locally in the extension. */
export interface ExtensionConfig {
  /** Base URL of the Bhapi capture gateway API. */
  apiUrl: string;
  /** Organisation / team group identifier. */
  groupId: string;
  /** Individual member identifier. */
  memberId: string;
  /** One-time setup code used during initial pairing with the portal. */
  setupCode: string;
  /** HMAC signing secret obtained after pairing. */
  signingSecret: string;
  /** Whether monitoring is currently enabled. */
  enabled: boolean;
}

/** Sensible defaults for a fresh installation. */
export const DEFAULT_CONFIG: ExtensionConfig = {
  apiUrl: "",
  groupId: "",
  memberId: "",
  setupCode: "",
  signingSecret: "",
  enabled: false,
};

// ---------------------------------------------------------------------------
// Internal messaging between content scripts, background worker, and popup
// ---------------------------------------------------------------------------

/** Discriminated message types used with chrome.runtime.sendMessage. */
export enum MessageType {
  /** Content script captured an event — forward it to the API. */
  CAPTURE_EVENT = "CAPTURE_EVENT",
  /** Content script detected that the user is on a supported AI platform. */
  PLATFORM_DETECTED = "PLATFORM_DETECTED",
  /** Popup or background pushed a config change. */
  CONFIG_UPDATE = "CONFIG_UPDATE",
  /** Popup requests a health / connection status check. */
  STATUS_CHECK = "STATUS_CHECK",
  /** Response to STATUS_CHECK with current connection info. */
  STATUS_RESPONSE = "STATUS_RESPONSE",
  /** Request current config from background worker. */
  GET_CONFIG = "GET_CONFIG",
  /** Response carrying the current config. */
  CONFIG_RESPONSE = "CONFIG_RESPONSE",
}

/** Union of all messages the extension can send internally. */
export type ExtensionMessage =
  | { type: MessageType.CAPTURE_EVENT; payload: CaptureEvent }
  | { type: MessageType.PLATFORM_DETECTED; payload: { platform: PlatformType; url: string } }
  | { type: MessageType.CONFIG_UPDATE; payload: Partial<ExtensionConfig> }
  | { type: MessageType.STATUS_CHECK }
  | { type: MessageType.STATUS_RESPONSE; payload: ConnectionStatus }
  | { type: MessageType.GET_CONFIG }
  | { type: MessageType.CONFIG_RESPONSE; payload: ExtensionConfig };

// ---------------------------------------------------------------------------
// Connection status (tracked in background worker)
// ---------------------------------------------------------------------------

export interface ConnectionStatus {
  connected: boolean;
  lastEventSentAt: string | null;
  lastError: string | null;
  eventsQueued: number;
  platform: PlatformType | null;
}

// ---------------------------------------------------------------------------
// Platform-specific DOM selectors
// ---------------------------------------------------------------------------

/** DOM selectors a platform adapter must provide for the monitor. */
export interface PlatformSelectors {
  /** CSS selector for the text input / prompt area. */
  inputSelector: string;
  /** CSS selector for the submit / send button. */
  submitButtonSelector: string;
  /** CSS selector for the container that holds AI responses. */
  responseContainerSelector: string;
  /** Optional: selector for individual response message elements. */
  responseMessageSelector?: string;
  /** Optional: selector that indicates a response is still streaming. */
  streamingIndicatorSelector?: string;
}
