/**
 * Bhapi AI Safety Monitor — Anthropic Claude Platform Adapter
 *
 * DOM selectors and helpers specific to claude.ai.
 *
 * NOTE: Claude's web interface uses React with frequently changing
 * class names (often hashed/obfuscated).  We prefer data attributes,
 * ARIA labels, and structural selectors where possible.
 */

import { PlatformSelectors } from "../../shared/types";

export const CLAUDE_SELECTORS: PlatformSelectors = {
  // Claude's prompt input area
  inputSelector: [
    "div[contenteditable='true'].ProseMirror",  // ProseMirror editor
    "div[contenteditable='true'][data-placeholder]", // Contenteditable with placeholder
    "fieldset div[contenteditable='true']",     // Fieldset-wrapped editor
    "div[contenteditable='true']",              // Generic contenteditable fallback
    "textarea[placeholder*='Reply']",           // Textarea variant
  ].join(", "),

  // The send button
  submitButtonSelector: [
    "button[aria-label='Send Message']",        // Aria label match
    "button[aria-label='Send message']",        // Case variant
    "fieldset button:last-of-type",             // Last button in the input fieldset
    "button[type='submit']",                    // Submit type button
  ].join(", "),

  // Container for Claude's responses
  responseContainerSelector: [
    "div[data-is-streaming]",                   // Streaming response container
    ".font-claude-message",                     // Claude-specific font class
    "div[class*='response']",                   // Broad response match
    "div[class*='message'][class*='assistant']", // Assistant message class
    ".conversation-content",                    // Conversation content area
  ].join(", "),

  // Individual response message elements
  responseMessageSelector: [
    "[data-is-streaming]",                      // Streaming or completed response
    ".font-claude-message",                     // Claude message font
    "div[data-message-author='assistant']",     // Author attribute
  ].join(", "),

  // Streaming indicator (Claude shows a cursor/loading animation during streaming)
  streamingIndicatorSelector: [
    "[data-is-streaming='true']",               // Active streaming data attribute
    ".animate-pulse",                           // Pulsing animation class
    "div[class*='cursor']",                     // Cursor animation
  ].join(", "),
};

/**
 * Attempt to extract the current prompt text from Claude's input area.
 */
export function getPromptText(): string {
  // Try ProseMirror contenteditable
  const proseMirror = document.querySelector<HTMLElement>(
    "div[contenteditable='true'].ProseMirror"
  );
  if (proseMirror) {
    return proseMirror.textContent || "";
  }

  // Try generic contenteditable
  const editable = document.querySelector<HTMLElement>(
    "div[contenteditable='true'][data-placeholder]"
  );
  if (editable) {
    return editable.textContent || "";
  }

  // Try textarea fallback
  const textarea = document.querySelector<HTMLTextAreaElement>(
    "textarea[placeholder*='Reply']"
  );
  if (textarea) {
    return textarea.value;
  }

  return "";
}

/**
 * Count the number of assistant response messages currently visible.
 */
export function countResponses(): number {
  const messages = document.querySelectorAll(
    CLAUDE_SELECTORS.responseMessageSelector || ""
  );
  return messages.length;
}
