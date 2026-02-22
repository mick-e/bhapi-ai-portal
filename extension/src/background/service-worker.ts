/**
 * Bhapi AI Safety Monitor — Background Service Worker
 *
 * Manifest V3 service worker that:
 *  1. Receives messages from content scripts and the popup.
 *  2. Forwards capture events to the Bhapi gateway API.
 *  3. Manages connection status and an offline event queue.
 *  4. Stores/retrieves configuration from chrome.storage.local.
 *
 * Firefox note: Firefox Manifest V3 uses `browser.*` APIs which are
 * largely compatible with `chrome.*`. A polyfill (webextension-polyfill)
 * can bridge any gaps.
 */

import { sendEvent, getConfig, checkStatus } from "../shared/api";
import {
  CaptureEvent,
  ConnectionStatus,
  ExtensionConfig,
  ExtensionMessage,
  MessageType,
  PlatformType,
} from "../shared/types";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

/** In-memory connection status (reset when the service worker restarts). */
let connectionStatus: ConnectionStatus = {
  connected: false,
  lastEventSentAt: null,
  lastError: null,
  eventsQueued: 0,
  platform: null,
};

/** Offline event queue — flushed when the API becomes reachable. */
const eventQueue: CaptureEvent[] = [];

/** Maximum number of events to hold in the offline queue. */
const MAX_QUEUE_SIZE = 500;

// ---------------------------------------------------------------------------
// Event queue management
// ---------------------------------------------------------------------------

function enqueueEvent(event: CaptureEvent): void {
  if (eventQueue.length >= MAX_QUEUE_SIZE) {
    // Drop oldest events when the queue is full
    eventQueue.shift();
  }
  eventQueue.push(event);
  connectionStatus.eventsQueued = eventQueue.length;
}

async function flushQueue(): Promise<void> {
  while (eventQueue.length > 0) {
    const event = eventQueue[0];
    const result = await sendEvent(event);
    if (result.ok) {
      eventQueue.shift();
      connectionStatus.eventsQueued = eventQueue.length;
      connectionStatus.lastEventSentAt = new Date().toISOString();
      connectionStatus.lastError = null;
      connectionStatus.connected = true;
    } else {
      // Stop flushing on first failure — retry later
      connectionStatus.lastError = result.error;
      connectionStatus.connected = false;
      break;
    }
  }
}

// ---------------------------------------------------------------------------
// Core event handler
// ---------------------------------------------------------------------------

async function handleCaptureEvent(event: CaptureEvent): Promise<void> {
  const config = await getConfig();
  if (!config.enabled) {
    return;
  }

  // Enrich event with stored identifiers if not already set
  const enrichedEvent: CaptureEvent = {
    ...event,
    groupId: event.groupId || config.groupId,
    memberId: event.memberId || config.memberId,
  };

  const result = await sendEvent(enrichedEvent);

  if (result.ok) {
    connectionStatus.connected = true;
    connectionStatus.lastEventSentAt = new Date().toISOString();
    connectionStatus.lastError = null;
  } else {
    connectionStatus.connected = false;
    connectionStatus.lastError = result.error;
    enqueueEvent(enrichedEvent);
  }
}

// ---------------------------------------------------------------------------
// Message listener
// ---------------------------------------------------------------------------

// chrome.runtime.onMessage — receives messages from content scripts & popup
// Firefox equivalent: browser.runtime.onMessage
chrome.runtime.onMessage.addListener(
  (
    message: ExtensionMessage,
    _sender: chrome.runtime.MessageSender,
    sendResponse: (response?: unknown) => void,
  ) => {
    switch (message.type) {
      case MessageType.CAPTURE_EVENT:
        handleCaptureEvent(message.payload)
          .then(() => sendResponse({ ok: true }))
          .catch((err) => sendResponse({ ok: false, error: String(err) }));
        // Return true to indicate we will respond asynchronously
        return true;

      case MessageType.PLATFORM_DETECTED:
        connectionStatus.platform = message.payload.platform;
        console.log(
          `[Bhapi] Platform detected: ${message.payload.platform} at ${message.payload.url}`,
        );
        sendResponse({ ok: true });
        return false;

      case MessageType.CONFIG_UPDATE:
        chrome.storage.local.set(message.payload, () => {
          sendResponse({ ok: true });
        });
        return true;

      case MessageType.STATUS_CHECK:
        // Return current connection status, also attempt a health check
        checkStatus()
          .then((result) => {
            connectionStatus.connected = result.ok;
            if (!result.ok) {
              connectionStatus.lastError = result.error;
            }
            sendResponse({
              type: MessageType.STATUS_RESPONSE,
              payload: connectionStatus,
            });
          })
          .catch(() => {
            sendResponse({
              type: MessageType.STATUS_RESPONSE,
              payload: connectionStatus,
            });
          });
        return true;

      case MessageType.GET_CONFIG:
        getConfig()
          .then((config) => {
            sendResponse({
              type: MessageType.CONFIG_RESPONSE,
              payload: config,
            });
          })
          .catch(() => {
            sendResponse({
              type: MessageType.CONFIG_RESPONSE,
              payload: null,
            });
          });
        return true;

      default:
        console.warn("[Bhapi] Unknown message type:", (message as { type: string }).type);
        sendResponse({ ok: false, error: "Unknown message type" });
        return false;
    }
  },
);

// ---------------------------------------------------------------------------
// Periodic queue flush via alarms
// ---------------------------------------------------------------------------

// chrome.alarms — Firefox equivalent: browser.alarms
chrome.alarms.create("bhapi-flush-queue", { periodInMinutes: 1 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "bhapi-flush-queue" && eventQueue.length > 0) {
    flushQueue().catch((err) => {
      console.error("[Bhapi] Queue flush failed:", err);
    });
  }
});

// ---------------------------------------------------------------------------
// Extension lifecycle
// ---------------------------------------------------------------------------

// Runs once when the service worker is first installed
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    console.log("[Bhapi] Extension installed — opening setup popup");
    // Could open the options page or popup on first install
  } else if (details.reason === "update") {
    console.log(`[Bhapi] Extension updated to ${chrome.runtime.getManifest().version}`);
  }
});

// Log when the service worker starts
console.log("[Bhapi] Background service worker started");
