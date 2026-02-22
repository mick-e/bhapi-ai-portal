/**
 * Bhapi AI Safety Monitor — Microsoft Copilot Platform Adapter
 *
 * DOM selectors and helpers specific to copilot.microsoft.com.
 *
 * NOTE: Microsoft Copilot's web UI uses a mix of React components and
 * Web Components (CIB — Conversational Intelligence Bot).  Selectors
 * target the outer shadow host boundaries where possible.
 */

import { PlatformSelectors } from "../../shared/types";

export const COPILOT_SELECTORS: PlatformSelectors = {
  // Copilot's prompt input area
  inputSelector: [
    "textarea#searchbox",                    // Main search/chat textarea
    "textarea[placeholder*='message']",      // Placeholder-based match
    "#searchbox",                            // ID-based fallback
    "cib-serp cib-action-bar textarea",      // CIB Web Component textarea
    ".input-container textarea",             // Container-based fallback
    "div[contenteditable='true']",           // Contenteditable variant
  ].join(", "),

  // The send / submit button
  submitButtonSelector: [
    "button[aria-label='Submit']",           // Aria label variant
    "button[aria-label='Send']",             // Send label variant
    "button.submit-button",                  // Class-based
    "cib-action-bar button[is='send-button']", // CIB send button
    "#submit-button",                        // ID-based
  ].join(", "),

  // Container for AI responses
  responseContainerSelector: [
    "cib-message-group[source='bot']",       // CIB bot message group
    ".response-message-group",               // Response group class
    "div[data-content='ai-message']",        // Data attribute based
    ".chat-messages-container",              // Chat messages container
    "#chat-messages",                        // ID-based container
  ].join(", "),

  // Individual response messages
  responseMessageSelector: [
    "cib-message[type='bot']",               // CIB bot message element
    ".bot-response",                         // Class-based bot response
    "[data-author='bot']",                   // Data attribute
  ].join(", "),

  // Loading / streaming indicator
  streamingIndicatorSelector: [
    "cib-typing-indicator",                  // CIB typing indicator
    ".typing-indicator",                     // Class-based
    ".response-streaming",                   // Streaming class
    "[class*='typing']",                     // Broad typing class match
  ].join(", "),
};

/**
 * Attempt to extract the current prompt text from Copilot's input area.
 */
export function getPromptText(): string {
  // Try the main searchbox textarea
  const textarea = document.querySelector<HTMLTextAreaElement>(
    "textarea#searchbox, textarea[placeholder*='message'], .input-container textarea"
  );
  if (textarea) {
    return textarea.value;
  }

  // Try contenteditable
  const editable = document.querySelector<HTMLElement>(
    "div[contenteditable='true']"
  );
  if (editable) {
    return editable.textContent || "";
  }

  return "";
}

/**
 * Count the number of bot response messages currently visible.
 */
export function countResponses(): number {
  const messages = document.querySelectorAll(
    COPILOT_SELECTORS.responseMessageSelector || ""
  );
  return messages.length;
}
