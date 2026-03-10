/**
 * Bhapi AI Safety Monitor — Character.ai Platform Adapter
 *
 * DOM selectors and helpers specific to character.ai and beta.character.ai.
 *
 * Character.ai is a companion chatbot platform where users form relationships
 * with AI characters. Bhapi monitors for emotional dependency patterns.
 */

import { PlatformSelectors } from "../../shared/types";

export const CHARACTERAI_SELECTORS: PlatformSelectors = {
  // Chat input textarea
  inputSelector: [
    "textarea[placeholder]",
    "div[contenteditable='true']",
    "#user-input",
  ].join(", "),

  // Send button
  submitButtonSelector: [
    "button[type='submit']",
    "button[aria-label='Send']",
    "button:has(svg[data-icon='paper-plane'])",
  ].join(", "),

  // AI character response containers
  responseContainerSelector: [
    "div[class*='chat-message']",
    "div[class*='msg-row']",
    "div[data-is-bot='true']",
  ].join(", "),

  // Individual character response messages
  responseMessageSelector: "div[data-is-bot='true'], div[class*='char-msg']",

  // Streaming/typing indicator
  streamingIndicatorSelector: [
    "div[class*='typing']",
    "div[class*='loading']",
    "span[class*='cursor']",
  ].join(", "),
};

/**
 * Attempt to extract the character name from the page.
 */
export function getCharacterName(): string {
  // Try the character name header
  const header = document.querySelector<HTMLElement>(
    "div[class*='chat-header'] span, h1[class*='character-name']"
  );
  if (header?.textContent) {
    return header.textContent.trim();
  }

  // Try page title (usually "CharacterName - Character.ai")
  const title = document.title;
  if (title && title.includes("-")) {
    return title.split("-")[0].trim();
  }

  return "Unknown Character";
}

/**
 * Extract the current prompt text from the input area.
 */
export function getPromptText(): string {
  const textarea = document.querySelector<HTMLTextAreaElement>(
    "textarea[placeholder], #user-input"
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
 * Count the number of character response messages visible.
 */
export function countResponses(): number {
  const messages = document.querySelectorAll(
    CHARACTERAI_SELECTORS.responseMessageSelector || ""
  );
  return messages.length;
}
