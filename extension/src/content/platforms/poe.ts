/**
 * Bhapi AI Safety Monitor — Poe (Quora) Platform Adapter
 *
 * DOM selectors and helpers specific to poe.com.
 *
 * Poe is a multi-model AI chat platform by Quora, offering access to
 * ChatGPT, Claude, Gemini, and custom bots. Bhapi monitors all
 * conversations regardless of which underlying model is used.
 */

import { PlatformSelectors } from "../../shared/types";

export const POE_SELECTORS: PlatformSelectors = {
  // Chat input
  inputSelector: [
    "textarea[class*='TextArea']",
    "textarea[placeholder]",
    "div[contenteditable='true']",
  ].join(", "),

  // Send button
  submitButtonSelector: [
    "button[class*='SendButton']",
    "button[aria-label='Send']",
    "button[type='submit']",
  ].join(", "),

  // Bot response containers
  responseContainerSelector: [
    "div[class*='Message_bot']",
    "div[class*='botMessage']",
    "div[data-bot-message]",
  ].join(", "),

  // Individual bot messages
  responseMessageSelector:
    "div[class*='Message_bot'], div[class*='botMessage'], div[data-bot-message]",

  // Streaming indicator
  streamingIndicatorSelector: [
    "div[class*='typing']",
    "div[class*='loading']",
    "button[class*='StopButton']",
  ].join(", "),
};

/**
 * Extract the current prompt text.
 */
export function getPromptText(): string {
  const textarea = document.querySelector<HTMLTextAreaElement>(
    "textarea[class*='TextArea'], textarea[placeholder]"
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
 * Count Poe bot response messages.
 */
export function countResponses(): number {
  const messages = document.querySelectorAll(
    POE_SELECTORS.responseMessageSelector || ""
  );
  return messages.length;
}
