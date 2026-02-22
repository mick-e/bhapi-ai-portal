/**
 * Bhapi AI Safety Monitor — Google Gemini Platform Adapter
 *
 * DOM selectors and helpers specific to gemini.google.com.
 *
 * NOTE: Google's Gemini UI uses Web Components and Shadow DOM extensively.
 * Some selectors target custom element tag names rather than class-based
 * selectors.  Selectors may need updates as Google iterates on the UI.
 */

import { PlatformSelectors } from "../../shared/types";

export const GEMINI_SELECTORS: PlatformSelectors = {
  // Gemini's prompt input area
  inputSelector: [
    "rich-textarea .ql-editor",              // Quill-based rich editor
    "rich-textarea textarea",                // Fallback textarea inside rich-textarea
    ".input-area textarea",                  // Simple textarea variant
    "div[contenteditable='true'][role='textbox']", // Contenteditable with textbox role
    ".text-input-field textarea",            // Material text field variant
  ].join(", "),

  // The send button
  submitButtonSelector: [
    "button[aria-label='Send message']",     // Primary send button
    "button.send-button",                    // Class-based send button
    ".input-area button[mat-icon-button]",   // Material icon button in input area
    "button[data-test-id='send-button']",    // Test ID variant
  ].join(", "),

  // Container for model responses
  responseContainerSelector: [
    "message-content",                       // Custom element for message content
    ".response-container",                   // Response container class
    ".model-response-text",                  // Model response text area
    "div[class*='response']",               // Broad response class match
    ".conversation-container",               // Conversation wrapper
  ].join(", "),

  // Individual response message elements
  responseMessageSelector: [
    "model-response",                        // Custom element
    ".model-response",                       // Class-based
    "[data-message-role='model']",           // Role attribute
  ].join(", "),

  // Streaming / loading indicator
  streamingIndicatorSelector: [
    ".loading-indicator",
    "mat-progress-bar",                      // Material progress bar
    ".response-loading",
    "[class*='loading']",
  ].join(", "),
};

/**
 * Attempt to extract the current prompt text from Gemini's input area.
 */
export function getPromptText(): string {
  // Try the Quill editor
  const quillEditor = document.querySelector<HTMLElement>(
    "rich-textarea .ql-editor"
  );
  if (quillEditor) {
    return quillEditor.textContent || "";
  }

  // Try a standard textarea
  const textarea = document.querySelector<HTMLTextAreaElement>(
    "rich-textarea textarea, .input-area textarea, .text-input-field textarea"
  );
  if (textarea) {
    return textarea.value;
  }

  // Try contenteditable
  const editable = document.querySelector<HTMLElement>(
    "div[contenteditable='true'][role='textbox']"
  );
  if (editable) {
    return editable.textContent || "";
  }

  return "";
}

/**
 * Count the number of model response messages currently visible.
 */
export function countResponses(): number {
  const messages = document.querySelectorAll(
    GEMINI_SELECTORS.responseMessageSelector || ""
  );
  return messages.length;
}
