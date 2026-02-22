/**
 * Bhapi AI Safety Monitor — xAI Grok Platform Adapter
 *
 * DOM selectors and helpers specific to grok.com and x.com/i/grok.
 *
 * NOTE: Grok's web interface can be accessed both at grok.com (standalone)
 * and within the X/Twitter app at x.com/i/grok.  The DOM structure may
 * differ between these two entry points.
 */

import { PlatformSelectors } from "../../shared/types";

export const GROK_SELECTORS: PlatformSelectors = {
  // Grok's prompt input area
  inputSelector: [
    "textarea[placeholder*='Ask']",             // Placeholder-based textarea
    "textarea[placeholder*='anything']",        // "Ask anything" variant
    "div[contenteditable='true'][role='textbox']", // Contenteditable textbox
    "div[contenteditable='true']",              // Generic contenteditable
    "textarea",                                 // Broad textarea fallback
  ].join(", "),

  // The send button
  submitButtonSelector: [
    "button[aria-label='Send']",                // Aria label match
    "button[aria-label='Submit']",              // Submit label variant
    "button[data-testid='send-button']",        // Test ID variant
    "button[type='submit']",                    // Submit type
    "form button:last-of-type",                 // Last button in form
  ].join(", "),

  // Container for Grok's responses
  responseContainerSelector: [
    "div[data-testid='message-container']",     // Test ID container
    ".message-list",                            // Message list class
    "div[class*='response']",                   // Broad response match
    "div[class*='message'][class*='bot']",      // Bot message class
    ".chat-container",                          // Chat container
  ].join(", "),

  // Individual response message elements
  responseMessageSelector: [
    "[data-testid='bot-message']",              // Test ID for bot messages
    "div[data-author='grok']",                  // Author attribute
    ".bot-message",                             // Class-based
    "[data-role='assistant']",                  // Role attribute
  ].join(", "),

  // Streaming indicator
  streamingIndicatorSelector: [
    ".typing-indicator",                        // Typing indicator class
    "[class*='streaming']",                     // Streaming class
    "[class*='loading']",                       // Loading class
    ".animate-pulse",                           // Pulse animation
  ].join(", "),
};

/**
 * Attempt to extract the current prompt text from Grok's input area.
 */
export function getPromptText(): string {
  // Try textarea first
  const textarea = document.querySelector<HTMLTextAreaElement>(
    "textarea[placeholder*='Ask'], textarea[placeholder*='anything'], textarea"
  );
  if (textarea) {
    return textarea.value;
  }

  // Try contenteditable
  const editable = document.querySelector<HTMLElement>(
    "div[contenteditable='true'][role='textbox'], div[contenteditable='true']"
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
    GROK_SELECTORS.responseMessageSelector || ""
  );
  return messages.length;
}
