/**
 * Bhapi AI Safety Monitor — Popup Script
 *
 * Controls the popup UI that appears when the user clicks the extension
 * icon in the browser toolbar.
 *
 * Chrome: uses chrome.runtime.sendMessage and chrome.storage.local.
 * Firefox equivalent: browser.runtime.sendMessage and browser.storage.local.
 */

import {
  ConnectionStatus,
  DEFAULT_CONFIG,
  ExtensionConfig,
  MessageType,
  PLATFORM_LABELS,
} from "../shared/types";
import { pairWithSetupCode, getConfig, saveConfig } from "../shared/api";

// ---------------------------------------------------------------------------
// DOM element references
// ---------------------------------------------------------------------------

const statusDot = document.getElementById("status-dot") as HTMLDivElement;
const statusLabel = document.getElementById("status-label") as HTMLSpanElement;

// Setup section
const setupSection = document.getElementById("setup-section") as HTMLDivElement;
const apiUrlInput = document.getElementById("api-url") as HTMLInputElement;
const setupCodeInput = document.getElementById("setup-code") as HTMLInputElement;
const btnPair = document.getElementById("btn-pair") as HTMLButtonElement;
const setupMessage = document.getElementById("setup-message") as HTMLDivElement;

// Monitor section
const monitorSection = document.getElementById("monitor-section") as HTMLDivElement;
const toggleEnabled = document.getElementById("toggle-enabled") as HTMLInputElement;
const infoGroup = document.getElementById("info-group") as HTMLElement;
const infoMember = document.getElementById("info-member") as HTMLElement;
const infoPlatform = document.getElementById("info-platform") as HTMLElement;
const infoLastEvent = document.getElementById("info-last-event") as HTMLElement;
const infoQueued = document.getElementById("info-queued") as HTMLElement;
const btnRefresh = document.getElementById("btn-refresh") as HTMLButtonElement;
const btnDisconnect = document.getElementById("btn-disconnect") as HTMLButtonElement;

// ---------------------------------------------------------------------------
// UI update helpers
// ---------------------------------------------------------------------------

function showSetup(): void {
  setupSection.classList.remove("hidden");
  monitorSection.classList.add("hidden");
}

function showMonitor(): void {
  setupSection.classList.add("hidden");
  monitorSection.classList.remove("hidden");
}

function setStatus(state: "connected" | "disconnected" | "unconfigured", label: string): void {
  statusDot.className = `status-dot ${state}`;
  statusLabel.textContent = label;
}

function showMessage(text: string, type: "success" | "error"): void {
  setupMessage.textContent = text;
  setupMessage.className = `message ${type}`;
  setupMessage.classList.remove("hidden");
}

function hideMessage(): void {
  setupMessage.classList.add("hidden");
}

function updateMonitorInfo(config: ExtensionConfig, status: ConnectionStatus | null): void {
  infoGroup.textContent = config.groupId || "--";
  infoMember.textContent = config.memberId || "--";

  if (status?.platform) {
    infoPlatform.textContent = PLATFORM_LABELS[status.platform] || status.platform;
  } else {
    infoPlatform.textContent = "Not detected";
  }

  if (status?.lastEventSentAt) {
    const date = new Date(status.lastEventSentAt);
    infoLastEvent.textContent = date.toLocaleTimeString();
  } else {
    infoLastEvent.textContent = "--";
  }

  infoQueued.textContent = String(status?.eventsQueued ?? 0);
  toggleEnabled.checked = config.enabled;
}

// ---------------------------------------------------------------------------
// Background communication
// ---------------------------------------------------------------------------

async function requestStatus(): Promise<ConnectionStatus | null> {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(
      { type: MessageType.STATUS_CHECK },
      (response) => {
        if (chrome.runtime.lastError) {
          console.warn("[Bhapi Popup] Status check failed:", chrome.runtime.lastError.message);
          resolve(null);
          return;
        }
        if (response?.type === MessageType.STATUS_RESPONSE) {
          resolve(response.payload as ConnectionStatus);
        } else {
          resolve(null);
        }
      },
    );
  });
}

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------

async function init(): Promise<void> {
  const config = await getConfig();

  const isConfigured = !!(config.apiUrl && config.groupId && config.signingSecret);

  if (!isConfigured) {
    setStatus("unconfigured", "Not configured");
    showSetup();

    // Pre-fill API URL if previously entered
    if (config.apiUrl) {
      apiUrlInput.value = config.apiUrl;
    }
    return;
  }

  // Show the monitor view
  showMonitor();

  // Request current status from the background worker
  const status = await requestStatus();

  if (status?.connected) {
    setStatus("connected", "Connected");
  } else if (status?.lastError) {
    setStatus("disconnected", `Error: ${status.lastError}`);
  } else {
    setStatus("disconnected", "Disconnected");
  }

  updateMonitorInfo(config, status);
}

// ---------------------------------------------------------------------------
// Event handlers
// ---------------------------------------------------------------------------

// Pair button — exchange setup code for credentials
btnPair.addEventListener("click", async () => {
  hideMessage();

  const apiUrl = apiUrlInput.value.trim().replace(/\/+$/, ""); // strip trailing slashes
  const setupCode = setupCodeInput.value.trim();

  if (!apiUrl) {
    showMessage("Please enter the Portal URL.", "error");
    return;
  }

  if (!setupCode) {
    showMessage("Please enter your setup code.", "error");
    return;
  }

  btnPair.disabled = true;
  btnPair.textContent = "Connecting...";

  try {
    const result = await pairWithSetupCode(apiUrl, setupCode);

    if (result.ok) {
      showMessage("Connected successfully!", "success");
      // Re-initialise to switch to monitor view
      setTimeout(() => init(), 1000);
    } else {
      showMessage(
        result.error || "Failed to connect. Check the URL and setup code.",
        "error",
      );
    }
  } catch (err) {
    showMessage(
      `Connection error: ${err instanceof Error ? err.message : String(err)}`,
      "error",
    );
  } finally {
    btnPair.disabled = false;
    btnPair.textContent = "Connect";
  }
});

// Toggle monitoring on/off
toggleEnabled.addEventListener("change", async () => {
  await saveConfig({ enabled: toggleEnabled.checked });
  if (toggleEnabled.checked) {
    setStatus("connected", "Monitoring enabled");
  } else {
    setStatus("disconnected", "Monitoring paused");
  }
});

// Refresh status
btnRefresh.addEventListener("click", async () => {
  btnRefresh.disabled = true;
  btnRefresh.textContent = "Refreshing...";

  const config = await getConfig();
  const status = await requestStatus();

  if (status?.connected) {
    setStatus("connected", "Connected");
  } else if (status?.lastError) {
    setStatus("disconnected", `Error: ${status.lastError}`);
  } else {
    setStatus("disconnected", "Disconnected");
  }

  updateMonitorInfo(config, status);

  btnRefresh.disabled = false;
  btnRefresh.textContent = "Refresh";
});

// Disconnect — clear credentials and return to setup
btnDisconnect.addEventListener("click", async () => {
  if (!confirm("Disconnect from the portal? You will need a new setup code to reconnect.")) {
    return;
  }

  await saveConfig({
    groupId: "",
    memberId: "",
    signingSecret: "",
    setupCode: "",
    enabled: false,
  });

  setStatus("unconfigured", "Disconnected");
  showSetup();
});

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

init().catch((err) => {
  console.error("[Bhapi Popup] Init failed:", err);
  setStatus("disconnected", "Initialisation error");
});
