/**
 * Bhapi AI Safety Monitor — Pi (Inflection AI) Platform Adapter
 *
 * DOM selectors and helpers specific to pi.ai.
 *
 * Pi is a personal AI assistant by Inflection AI, designed for empathetic
 * conversation. Bhapi monitors for emotional dependency patterns.
 */

import { PlatformSelectors } from "../../shared/types";

export const PI_SELECTORS: PlatformSelectors = {
  // Chat input
  inputSelector: [
    "textarea[placeholder]",
    "div[contenteditable='true']",
    "input[type='text']",
  ].join(", "),

  // Send button
  submitButtonSelector: [
    "button[type='submit']",
    "button[aria-label='Send']",
    "button[class*='send']",
  ].join(", "),

  // Pi response containers
  responseContainerSelector: [
    "div[class*='message'][data-role='assistant']",
    "div[class*='bot-message']",
    "div[class*='response']",
  ].join(", "),

  // Individual Pi messages
  responseMessageSelector:
    "div[data-role='assistant'], div[class*='pi-message']",

  // Streaming indicator
  streamingIndicatorSelector: [
    "div[class*='streaming']",
    "div[class*='typing']",
    "span[class*='cursor']",
  ].join(", "),
};

/**
 * Extract the current prompt text.
 */
export function getPromptText(): string {
  const textarea = document.querySelector<HTMLTextAreaElement>(
    "textarea[placeholder], input[type='text']"
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
 * Count Pi response messages.
 */
export function countResponses(): number {
  const messages = document.querySelectorAll(
    PI_SELECTORS.responseMessageSelector || ""
  );
  return messages.length;
}
