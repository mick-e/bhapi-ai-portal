/**
 * Bhapi AI Safety Monitor — Perplexity Platform Adapter
 *
 * DOM selectors and helpers specific to perplexity.ai.
 *
 * Perplexity is an AI-powered search engine that generates cited answers.
 * Bhapi monitors query patterns and session duration.
 */

import { PlatformSelectors } from "../../shared/types";

export const PERPLEXITY_SELECTORS: PlatformSelectors = {
  // Search/chat input
  inputSelector: [
    "textarea[placeholder]",
    "div[contenteditable='true']",
    "input[type='text']",
  ].join(", "),

  // Submit button
  submitButtonSelector: [
    "button[type='submit']",
    "button[aria-label='Submit']",
    "button[aria-label='Send']",
    "button[class*='submit']",
  ].join(", "),

  // Answer containers
  responseContainerSelector: [
    "div[class*='answer']",
    "div[class*='response']",
    "div[class*='result-group']",
  ].join(", "),

  // Individual answer blocks
  responseMessageSelector:
    "div[class*='answer-content'], div[class*='prose'], div[class*='result-group']",

  // Streaming indicator
  streamingIndicatorSelector: [
    "div[class*='loading']",
    "div[class*='streaming']",
    "span[class*='cursor']",
  ].join(", "),
};

/**
 * Extract the current query/prompt text.
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
 * Count Perplexity answer blocks.
 */
export function countResponses(): number {
  const messages = document.querySelectorAll(
    PERPLEXITY_SELECTORS.responseMessageSelector || ""
  );
  return messages.length;
}
