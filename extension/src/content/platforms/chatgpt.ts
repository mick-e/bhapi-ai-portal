/**
 * Bhapi AI Safety Monitor — ChatGPT Platform Adapter
 *
 * DOM selectors and helpers specific to chatgpt.com.
 *
 * NOTE: These selectors are based on ChatGPT's DOM structure as of early 2026.
 * OpenAI frequently updates their frontend, so selectors may need periodic
 * maintenance.  The monitor falls back gracefully if selectors do not match.
 */

import { PlatformSelectors } from "../../shared/types";

export const CHATGPT_SELECTORS: PlatformSelectors = {
  // The main prompt textarea (ChatGPT uses a contenteditable div or a <textarea>
  // depending on the version; we target the most common wrapper).
  inputSelector: [
    "textarea[data-id='root']",           // Legacy textarea
    "#prompt-textarea",                    // Current prompt textarea id
    "div[contenteditable='true']",         // Contenteditable variant
    "form textarea",                       // Fallback: any textarea in the form
  ].join(", "),

  // The send / submit button
  submitButtonSelector: [
    "button[data-testid='send-button']",   // data-testid variant
    "form button[aria-label='Send']",      // aria-label variant
    "form button:has(svg)",                // Fallback: icon button inside form
  ].join(", "),

  // Container holding AI response messages
  responseContainerSelector: [
    "div[data-testid='conversation-turn-'][data-scroll-anchor]",  // Conversation turns
    "div.markdown",                        // Markdown rendered response blocks
    "div[class*='agent-turn']",            // Agent turn containers
    "main div.group",                      // Grouped message containers
  ].join(", "),

  // Individual response message elements
  responseMessageSelector: "div[data-message-author-role='assistant']",

  // Streaming indicator (the pulsing cursor / "thinking" animation)
  streamingIndicatorSelector: [
    "div[class*='result-streaming']",
    "span.cursor",
    "div[class*='thinking']",
  ].join(", "),
};

/**
 * Attempt to extract the current prompt text from the input area.
 * Returns an empty string if the input cannot be found.
 */
export function getPromptText(): string {
  // Try textarea first
  const textarea = document.querySelector<HTMLTextAreaElement>(
    "#prompt-textarea, textarea[data-id='root'], form textarea"
  );
  if (textarea) {
    return textarea.value;
  }

  // Try contenteditable div
  const editable = document.querySelector<HTMLElement>(
    "div[contenteditable='true']"
  );
  if (editable) {
    return editable.textContent || "";
  }

  return "";
}

/**
 * Count the number of assistant response messages currently visible.
 */
export function countResponses(): number {
  const messages = document.querySelectorAll(
    CHATGPT_SELECTORS.responseMessageSelector || ""
  );
  return messages.length;
}
