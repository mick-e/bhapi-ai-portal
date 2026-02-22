"""DNS proxy configuration."""

import os

# Upstream DNS server
UPSTREAM_DNS = os.getenv("UPSTREAM_DNS", "8.8.8.8")
UPSTREAM_PORT = int(os.getenv("UPSTREAM_PORT", "53"))

# Listen address
LISTEN_HOST = os.getenv("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "53"))

# Capture gateway URL
CAPTURE_API_URL = os.getenv("CAPTURE_API_URL", "http://localhost:8000/api/v1/capture/dns-events")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")

# Monitored AI platform domains
MONITORED_DOMAINS = {
    "chat.openai.com": "chatgpt",
    "chatgpt.com": "chatgpt",
    "gemini.google.com": "gemini",
    "copilot.microsoft.com": "copilot",
    "claude.ai": "claude",
    "grok.com": "grok",
    "x.com": "grok",
}

# Group/member mapping (configured per deployment)
GROUP_ID = os.getenv("GROUP_ID", "")
MEMBER_ID = os.getenv("MEMBER_ID", "")
