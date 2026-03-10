/**
 * Bhapi AI Safety Monitor — Replika Platform Adapter
 *
 * DOM selectors and helpers specific to web.replika.com.
 *
 * Replika is an AI companion app that can form deep emotional connections
 * with users. Bhapi monitors for emotional dependency patterns.
 */

import { PlatformSelectors } from "../../shared/types";

export const REPLIKA_SELECTORS: PlatformSelectors = {
  // Chat input area
  inputSelector: [
    "textarea[placeholder]",
    "input[type='text'][placeholder]",
    "div[contenteditable='true']",
  ].join(", "),

  // Send button
  submitButtonSelector: [
    "button[type='submit']",
    "button[aria-label='Send message']",
    "button[class*='send']",
  ].join(", "),

  // Replika response containers
  responseContainerSelector: [
    "div[class*='ChatMessage']",
    "div[class*='message-bubble']",
    "div[data-author='replika']",
  ].join(", "),

  // Individual Replika messages
  responseMessageSelector:
    "div[data-author='replika'], div[class*='replika-message']",

  // Typing indicator
  streamingIndicatorSelector: [
    "div[class*='typing-indicator']",
    "div[class*='TypingIndicator']",
    "span[class*='dot-animation']",
  ].join(", "),
};

/**
 * Detect the current Replika relationship mode.
 * Replika offers Friend, Romantic Partner, and Mentor modes.
 */
export function getRelationshipMode(): string {
  // Look for relationship mode indicators in the UI
  const modeEl = document.querySelector<HTMLElement>(
    "div[class*='relationship'], span[class*='mode']"
  );
  if (modeEl?.textContent) {
    return modeEl.textContent.trim();
  }
  return "unknown";
}

/**
 * Extract the current prompt text.
 */
export function getPromptText(): string {
  const textarea = document.querySelector<HTMLTextAreaElement>(
    "textarea[placeholder], input[type='text'][placeholder]"
  );
  if (textarea) {
    return textarea.value;
  }

  const editable = document.querySelector<HTMLElement>(
    "div[contenteditable='true']"
  );
  if (editable) {
    return editable.textContent || "";
  }

  return "";
}

/**
 * Count Replika response messages.
 */
export function countResponses(): number {
  const messages = document.querySelectorAll(
    REPLIKA_SELECTORS.responseMessageSelector || ""
  );
  return messages.length;
}
