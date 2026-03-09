/**
 * Blocking enforcement content script.
 * Polls /api/v1/blocking/active-rules for the paired group and
 * blocks/unblocks AI platform submissions accordingly.
 */

const POLL_INTERVAL_MS = 30000; // 30 seconds
const API_BASE = ""; // Filled from storage

// Platform-specific selectors for submission elements
const PLATFORM_SELECTORS = {
  "chat.openai.com": {
    form: 'form[data-testid="composer-form"], form.stretch',
    input: 'textarea[data-id="root"], #prompt-textarea',
    submit: 'button[data-testid="send-button"], button.absolute',
  },
  "gemini.google.com": {
    form: ".input-area-container",
    input: '.ql-editor, textarea[aria-label]',
    submit: 'button[aria-label="Send message"], .send-button',
  },
  "claude.ai": {
    form: ".composer-parent",
    input: '[contenteditable="true"], .ProseMirror',
    submit: 'button[aria-label="Send Message"]',
  },
  "copilot.microsoft.com": {
    form: "#searchbox",
    input: 'textarea, [contenteditable="true"]',
    submit: 'button[aria-label="Submit"]',
  },
  "grok.com": {
    form: "form",
    input: "textarea",
    submit: 'button[type="submit"]',
  },
};

let currentRules = [];
let isBlocked = false;
let blockedOverlay = null;

/**
 * Get the current platform from the hostname.
 */
function getCurrentPlatform() {
  const host = window.location.hostname;
  for (const platform of Object.keys(PLATFORM_SELECTORS)) {
    if (host.includes(platform.replace("www.", ""))) {
      return platform;
    }
  }
  return null;
}

/**
 * Create a blocking overlay that prevents interaction.
 */
function createBlockOverlay(reason) {
  if (blockedOverlay) return;

  blockedOverlay = document.createElement("div");
  blockedOverlay.id = "bhapi-block-overlay";
  blockedOverlay.style.cssText = `
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0, 0, 0, 0.85); z-index: 999999;
    display: flex; align-items: center; justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  `;
  blockedOverlay.innerHTML = `
    <div style="background: white; border-radius: 16px; padding: 48px; max-width: 480px; text-align: center;">
      <div style="font-size: 48px; margin-bottom: 16px;">&#x1f6e1;&#xfe0f;</div>
      <h2 style="color: #1a1a1a; font-size: 24px; margin: 0 0 12px;">Access Blocked</h2>
      <p style="color: #666; font-size: 16px; line-height: 1.5; margin: 0 0 8px;">
        ${reason || "This AI platform is currently blocked by your guardian."}
      </p>
      <p style="color: #999; font-size: 13px; margin: 0;">
        Managed by <strong style="color: #FF6B35;">bhapi</strong>
      </p>
    </div>
  `;
  document.body.appendChild(blockedOverlay);
}

/**
 * Remove the blocking overlay.
 */
function removeBlockOverlay() {
  if (blockedOverlay) {
    blockedOverlay.remove();
    blockedOverlay = null;
  }
}

/**
 * Disable form submission on the current platform.
 */
function blockSubmission(platform) {
  const selectors = PLATFORM_SELECTORS[platform];
  if (!selectors) return;

  // Disable submit buttons
  document.querySelectorAll(selectors.submit).forEach((btn) => {
    btn.disabled = true;
    btn.style.opacity = "0.3";
    btn.style.pointerEvents = "none";
    btn.dataset.bhapiBlocked = "true";
  });

  // Disable input areas
  document.querySelectorAll(selectors.input).forEach((input) => {
    if (input.tagName === "TEXTAREA") {
      input.disabled = true;
    } else {
      input.contentEditable = "false";
    }
    input.style.opacity = "0.3";
    input.dataset.bhapiBlocked = "true";
  });
}

/**
 * Re-enable form submission on the current platform.
 */
function unblockSubmission(platform) {
  const selectors = PLATFORM_SELECTORS[platform];
  if (!selectors) return;

  document.querySelectorAll("[data-bhapi-blocked]").forEach((el) => {
    el.disabled = false;
    el.style.opacity = "";
    el.style.pointerEvents = "";
    if (el.dataset.bhapiBlocked) {
      delete el.dataset.bhapiBlocked;
    }
    if (el.contentEditable === "false" && el.matches(selectors.input)) {
      el.contentEditable = "true";
    }
  });
}

/**
 * Poll the backend for active block rules.
 */
async function pollBlockRules() {
  try {
    const storage = await chrome.storage.local.get(["groupId", "apiBase", "signingSecret"]);
    if (!storage.groupId) return;

    const apiBase = storage.apiBase || "";
    const response = await fetch(
      `${apiBase}/api/v1/blocking/active-rules?group_id=${storage.groupId}`,
      {
        headers: {
          "X-Signing-Secret": storage.signingSecret || "",
        },
      }
    );

    if (!response.ok) return;
    const data = await response.json();
    currentRules = data.rules || data || [];

    const platform = getCurrentPlatform();
    if (!platform) return;

    // Check if current platform is blocked
    const platformBlocked = currentRules.some(
      (rule) =>
        rule.status === "active" &&
        (!rule.platform || rule.platform === "all" || rule.platform === platform)
    );

    if (platformBlocked && !isBlocked) {
      isBlocked = true;
      const rule = currentRules.find((r) => r.status === "active");
      blockSubmission(platform);
      createBlockOverlay(rule?.reason);
    } else if (!platformBlocked && isBlocked) {
      isBlocked = false;
      unblockSubmission(platform);
      removeBlockOverlay();
    }
  } catch (err) {
    console.debug("[bhapi] Block rule poll failed:", err.message);
  }
}

// Start polling
pollBlockRules();
setInterval(pollBlockRules, POLL_INTERVAL_MS);

// Re-check when page content changes (SPA navigation)
const observer = new MutationObserver(() => {
  if (isBlocked) {
    const platform = getCurrentPlatform();
    if (platform) blockSubmission(platform);
  }
});
observer.observe(document.body, { childList: true, subtree: true });
