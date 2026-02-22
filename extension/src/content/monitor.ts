/**
 * Bhapi AI Safety Monitor — Content Script (DOM Monitor)
 *
 * Injected into AI platform pages by the manifest's content_scripts config.
 * Responsibilities:
 *  1. Detect which AI platform we are on.
 *  2. Set up a MutationObserver to watch for prompt submissions and responses.
 *  3. Generate per-page session IDs.
 *  4. Forward capture events to the background service worker.
 *
 * This script is intentionally non-intrusive:
 *  - It does NOT modify the DOM.
 *  - It does NOT intercept network requests.
 *  - It only reads DOM state to detect usage events.
 *
 * Chrome: uses chrome.runtime.sendMessage.
 * Firefox equivalent: browser.runtime.sendMessage.
 */

import { detectPlatform } from "./detector";
import {
  CaptureEvent,
  EventType,
  ExtensionMessage,
  MessageType,
  PlatformSelectors,
  PlatformType,
} from "../shared/types";

// Platform adapters
import { CHATGPT_SELECTORS, getPromptText as chatgptPrompt, countResponses as chatgptCount } from "./platforms/chatgpt";
import { GEMINI_SELECTORS, getPromptText as geminiPrompt, countResponses as geminiCount } from "./platforms/gemini";
import { COPILOT_SELECTORS, getPromptText as copilotPrompt, countResponses as copilotCount } from "./platforms/copilot";
import { CLAUDE_SELECTORS, getPromptText as claudePrompt, countResponses as claudeCount } from "./platforms/claude";
import { GROK_SELECTORS, getPromptText as grokPrompt, countResponses as grokCount } from "./platforms/grok";

// ---------------------------------------------------------------------------
// Session management
// ---------------------------------------------------------------------------

/** Generate a random session ID for this page load. */
function generateSessionId(): string {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return Array.from(array)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

const SESSION_ID = generateSessionId();

// ---------------------------------------------------------------------------
// Platform detection
// ---------------------------------------------------------------------------

const currentPlatform = detectPlatform(window.location.href);

if (!currentPlatform) {
  // Not on a recognised AI platform — should not happen since the manifest
  // restricts content_scripts to known domains, but exit gracefully.
  console.log("[Bhapi] URL not recognised as an AI platform, monitor inactive.");
} else {
  console.log(`[Bhapi] Monitoring ${currentPlatform} — session ${SESSION_ID}`);
  initMonitor(currentPlatform);
}

// ---------------------------------------------------------------------------
// Platform adapter resolution
// ---------------------------------------------------------------------------

interface PlatformAdapter {
  selectors: PlatformSelectors;
  getPromptText: () => string;
  countResponses: () => number;
}

function getAdapter(platform: PlatformType): PlatformAdapter {
  switch (platform) {
    case "chatgpt":
      return { selectors: CHATGPT_SELECTORS, getPromptText: chatgptPrompt, countResponses: chatgptCount };
    case "gemini":
      return { selectors: GEMINI_SELECTORS, getPromptText: geminiPrompt, countResponses: geminiCount };
    case "copilot":
      return { selectors: COPILOT_SELECTORS, getPromptText: copilotPrompt, countResponses: copilotCount };
    case "claude":
      return { selectors: CLAUDE_SELECTORS, getPromptText: claudePrompt, countResponses: claudeCount };
    case "grok":
      return { selectors: GROK_SELECTORS, getPromptText: grokPrompt, countResponses: grokCount };
  }
}

// ---------------------------------------------------------------------------
// Event dispatch
// ---------------------------------------------------------------------------

/**
 * Send a capture event to the background service worker.
 */
function sendCaptureEvent(eventType: EventType, metadata?: Record<string, unknown>): void {
  const event: CaptureEvent = {
    groupId: "",   // Will be enriched by the background worker from config
    memberId: "",  // Will be enriched by the background worker from config
    platform: currentPlatform!,
    sessionId: SESSION_ID,
    eventType,
    timestamp: new Date().toISOString(),
    metadata,
  };

  const message: ExtensionMessage = {
    type: MessageType.CAPTURE_EVENT,
    payload: event,
  };

  chrome.runtime.sendMessage(message).catch((err) => {
    // Service worker may not be ready yet — this is non-fatal
    console.warn("[Bhapi] Failed to send capture event:", err);
  });
}

/**
 * Notify the background worker that we detected a supported platform.
 */
function sendPlatformDetected(platform: PlatformType): void {
  const message: ExtensionMessage = {
    type: MessageType.PLATFORM_DETECTED,
    payload: { platform, url: window.location.href },
  };

  chrome.runtime.sendMessage(message).catch(() => {
    // Non-fatal — service worker may be starting up
  });
}

// ---------------------------------------------------------------------------
// Core monitoring logic
// ---------------------------------------------------------------------------

function initMonitor(platform: PlatformType): void {
  const adapter = getAdapter(platform);

  // Notify background that we detected this platform
  sendPlatformDetected(platform);

  // Track state to detect changes
  let lastResponseCount = adapter.countResponses();
  let isStreaming = false;
  let submitWatched = false;

  // Send session_started event
  sendCaptureEvent("session_started", {
    url: window.location.href,
    userAgent: navigator.userAgent,
  });

  // ------------------------------------------
  // Submit button click interception
  // ------------------------------------------

  function attachSubmitListener(): void {
    if (submitWatched) return;

    const submitBtn = document.querySelector(adapter.selectors.submitButtonSelector);
    if (!submitBtn) return;

    submitBtn.addEventListener("click", () => {
      const promptText = adapter.getPromptText();
      sendCaptureEvent("prompt_submitted", {
        promptLength: promptText.length,
        // We intentionally do NOT capture prompt content for privacy.
        // Only the length is recorded for usage analytics.
      });
    });

    submitWatched = true;
  }

  // Also detect Enter key submission on the input area
  function attachKeyboardListener(): void {
    const input = document.querySelector(adapter.selectors.inputSelector);
    if (!input) return;

    input.addEventListener("keydown", (event) => {
      const kbEvent = event as KeyboardEvent;
      // Most AI platforms submit on Enter (without Shift)
      if (kbEvent.key === "Enter" && !kbEvent.shiftKey) {
        // Small delay to let the platform process the submission
        setTimeout(() => {
          const promptText = adapter.getPromptText();
          // Only fire if the input was cleared (indicating submission occurred)
          if (promptText.length === 0) {
            sendCaptureEvent("prompt_submitted", {
              promptLength: 0, // Text already cleared
              submittedVia: "keyboard",
            });
          }
        }, 200);
      }
    });
  }

  // ------------------------------------------
  // MutationObserver for response detection
  // ------------------------------------------

  const observer = new MutationObserver((_mutations) => {
    // Re-attach submit listener if DOM has changed (SPA navigation)
    if (!submitWatched) {
      attachSubmitListener();
      attachKeyboardListener();
    }

    // Check for new responses
    const currentCount = adapter.countResponses();
    if (currentCount > lastResponseCount) {
      // New response(s) appeared
      const newResponses = currentCount - lastResponseCount;
      lastResponseCount = currentCount;

      sendCaptureEvent("response_received", {
        responseIndex: currentCount,
        newResponseCount: newResponses,
      });
    }

    // Check streaming state
    const streamingSelector = adapter.selectors.streamingIndicatorSelector;
    if (streamingSelector) {
      const streamingElement = document.querySelector(streamingSelector);
      const nowStreaming = !!streamingElement;

      if (nowStreaming && !isStreaming) {
        // Streaming started — we already captured this via response_received
        isStreaming = true;
      } else if (!nowStreaming && isStreaming) {
        // Streaming ended
        isStreaming = false;
        // Could emit a "response_complete" event here if needed
      }
    }
  });

  // Observe the entire document body for changes.
  // This is broad but necessary because AI platforms dynamically render
  // responses in various parts of the DOM.
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    // We do NOT observe attributes or characterData to minimise overhead.
  });

  // Initial attachment attempts
  attachSubmitListener();
  attachKeyboardListener();

  // ------------------------------------------
  // SPA navigation detection
  // ------------------------------------------

  // AI platforms are SPAs — detect URL changes via popstate and polling.
  let lastUrl = window.location.href;

  window.addEventListener("popstate", () => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      submitWatched = false;
      lastResponseCount = 0;
      sendCaptureEvent("session_started", {
        url: window.location.href,
        navigationType: "popstate",
      });
    }
  });

  // Periodic URL check (catches pushState which doesn't fire popstate)
  setInterval(() => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      submitWatched = false;
      lastResponseCount = 0;
      sendCaptureEvent("session_started", {
        url: window.location.href,
        navigationType: "pushstate",
      });
    }
  }, 2000);

  // ------------------------------------------
  // Cleanup on page unload
  // ------------------------------------------

  window.addEventListener("beforeunload", () => {
    sendCaptureEvent("session_ended", {
      url: window.location.href,
      totalResponses: lastResponseCount,
    });
    observer.disconnect();
  });
}
