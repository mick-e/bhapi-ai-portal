# Bhapi AI Safety Monitor — Store Listings

Complete copy and assets checklist for all browser extension stores.

---

## Shared Metadata

| Field | Value |
|-------|-------|
| **Extension name** | Bhapi AI Safety Monitor |
| **Version** | 1.0.0 |
| **Author/Publisher** | Bhapi |
| **Website** | https://bhapi.ai |
| **Support URL** | https://bhapi.ai |
| **Support email** | support@bhapi.ai |
| **Privacy policy** | https://bhapi.ai/legal/privacy |
| **Terms of service** | https://bhapi.ai/legal/terms |
| **Category** | Education |
| **Language** | English (primary), French, Spanish, German, Portuguese, Italian |

---

## Short Description (132 chars max — used by Chrome, Edge)

```
Monitor your family's AI usage across ChatGPT, Claude, Gemini, Copilot, Grok, and 5 more platforms. Real-time safety alerts.
```

## Summary Description (250 chars — used by Firefox)

```
Bhapi AI Safety Monitor tracks children's AI platform interactions for families, schools, and clubs. Monitors 10 platforms including ChatGPT, Claude, Gemini, and Character.AI. Privacy-first: captures usage metadata only, never conversation content.
```

## Full Description (all stores)

```
Bhapi AI Safety Monitor — Keep your family safe with AI

Bhapi is the first browser extension purpose-built for monitoring children's AI platform usage. Whether you're a parent, school administrator, or club manager, Bhapi gives you visibility into how young people interact with AI — without reading their conversations.

MONITORS 10 AI PLATFORMS
- ChatGPT (OpenAI)
- Google Gemini
- Microsoft Copilot
- Claude (Anthropic)
- Grok (xAI)
- Character.AI
- Replika
- Pi (Inflection)
- Perplexity
- Poe (Quora)

KEY FEATURES
- Real-time session tracking — know when and how long AI platforms are used
- Safety alerts — get notified about concerning usage patterns
- Time budgets — set daily AI screen time limits per child
- Bedtime mode — automatically block AI platforms during sleep hours
- Platform blocking — block specific AI platforms with parent approval workflow
- Spend tracking — monitor API costs across OpenAI, Anthropic, Google, Microsoft, and xAI

PRIVACY FIRST
Bhapi captures only usage metadata:
- Session start/end times
- Platform visited
- Prompt count and length (NOT the actual text)
- Response count

We NEVER read, store, or transmit conversation content. All data is encrypted in transit and at rest.

FOR FAMILIES
- Monitor all your children from a single dashboard
- Set individual time budgets and alert preferences
- Weekly safety reports delivered by email
- Panic button for children to flag uncomfortable AI interactions
- AI literacy modules to educate kids about safe AI use

FOR SCHOOLS & CLUBS
- Manage classes and groups with per-seat billing
- Clever and ClassLink SIS integration for automatic student rostering
- Google Workspace and Microsoft Entra SSO
- Safeguarding reports for school administrators
- COPPA, GDPR, and LGPD compliant

HOW IT WORKS
1. Create an account at https://bhapi.ai (14-day free trial)
2. Install this extension on your child's browser
3. Enter the setup code from your Bhapi dashboard
4. Start receiving safety insights and alerts

COMPLIANCE
- COPPA (Children's Online Privacy Protection Act)
- GDPR (EU General Data Protection Regulation)
- LGPD (Brazil's Lei Geral de Protecao de Dados)
- EU AI Act transparency requirements

PRICING
- Family plan: $9.99/month (up to 5 members)
- School and club plans: per-seat pricing
- 14-day free trial, no credit card required

Learn more at https://bhapi.ai
```

---

## Store-Specific Notes

### Microsoft Edge Add-ons

- **Dashboard**: https://partner.microsoft.com/dashboard/microsoftedge/
- **Zip file**: `bhapi-edge.zip`
- **Account cost**: Free
- **Review time**: 1-7 business days
- **Additional fields**:
  - Testing notes: "Extension monitors AI platform pages. Load https://chatgpt.com to test the content script injection. The popup shows connection status."

### Firefox Add-ons (AMO)

- **Dashboard**: https://addons.mozilla.org/developers/
- **Zip file**: `bhapi-firefox.zip`
- **Source zip**: `bhapi-firefox-source.zip` (required — we use webpack)
- **Account cost**: Free
- **Review time**: 1-5 business days
- **Build instructions** (paste when asked):
  ```
  npm install
  npm run build
  Output is in the dist/ directory.
  Node.js 18+ required.
  ```
- **Additional notes for reviewers**:
  ```
  This extension monitors AI platform usage for child safety. It injects a
  content script on supported AI platform domains (ChatGPT, Gemini, Claude,
  etc.) that detects session activity (prompt submissions and responses) via
  DOM observation. It does NOT read conversation content — only counts and
  lengths are captured. Events are sent to the user's configured Bhapi portal
  instance via HTTPS. The extension requires pairing with a Bhapi account at
  https://bhapi.ai before it sends any data.
  ```

### Chrome Web Store

- **Dashboard**: https://chrome.google.com/webstore/devconsole
- **Zip file**: `bhapi-chrome.zip`
- **Account cost**: $5 one-time registration fee
- **Review time**: 1-3 business days
- **Single purpose description**:
  ```
  Monitor children's AI platform usage for safety compliance. Tracks session
  activity on ChatGPT, Gemini, Claude, Copilot, Grok, Character.AI, Replika,
  Pi, Perplexity, and Poe. Sends usage metadata (not conversation content) to
  the parent's Bhapi safety dashboard.
  ```
- **Permission justifications**:
  | Permission | Justification |
  |------------|---------------|
  | `tabs` | Detect which AI platform tab is active to show correct status in popup |
  | `activeTab` | Read the current tab URL to identify the AI platform being visited |
  | `storage` | Store extension configuration (API URL, group/member IDs, signing secret) |
  | Host permissions (10 AI domains) | Inject content script to monitor AI platform usage patterns |

- **Data usage declarations** (Privacy Practices tab):
  | Data type | Collected? | Usage |
  |-----------|------------|-------|
  | Website content | No | We do NOT collect page content |
  | Web history | Yes | We collect which AI platform domains are visited (not full URLs) |
  | User activity | Yes | We collect session duration and prompt/response counts |
  | Personally identifiable information | No | |
  | Authentication info | No | |
  | Location | No | |
  | Financial info | No | |
  | Health info | No | |
  | Communications | No | We do NOT read or store conversation content |

  Certify that:
  - Data is NOT sold to third parties
  - Data is NOT used for purposes unrelated to the extension's core functionality
  - Data is NOT used for creditworthiness or lending purposes

### Safari (Mac App Store)

- **Dashboard**: https://appstoreconnect.apple.com
- **Build**: Open `extension/safari/SafariBhapiExtension` in Xcode, Archive, distribute
- **Account cost**: $99/year Apple Developer Program
- **Review time**: 1-7 business days
- **App Store category**: Education
- **Age rating**: 4+ (the extension itself is safe; it monitors AI usage)
- **App Store description**: Use the Full Description above
- **Keywords** (100 chars max):
  ```
  AI safety,parental controls,ChatGPT monitor,child safety,screen time,AI monitoring
  ```
- **What's New** (for v1.0.0):
  ```
  Initial release. Monitors 10 AI platforms including ChatGPT, Claude, Gemini, Copilot, and Grok.
  ```

---

## Required Screenshots

All stores require at least 1 screenshot. Recommended: 3-5.

### Screenshot List

| # | Description | Dimensions | What to capture |
|---|-------------|------------|-----------------|
| 1 | Extension popup (connected) | 1280x800 | Open ChatGPT, click extension icon, show the popup with "Connected" status and monitoring info |
| 2 | Extension popup (setup) | 1280x800 | Show the popup in setup/pairing mode with the form fields |
| 3 | Bhapi dashboard | 1280x800 | Show the bhapi.ai dashboard with activity data, alerts, and safety scores |
| 4 | Safety alerts | 1280x800 | Show the alerts page with example notifications |
| 5 | Platform blocking | 1280x800 | Show the blocking rules page with configured rules |

### How to take screenshots

**Chrome/Edge** (1280x800):
1. Set browser window to exactly 1280x800: press F12, click the device toolbar icon, set to "Responsive" 1280x800
2. Navigate to the AI platform or dashboard
3. Click the Bhapi extension icon to open popup
4. Press Ctrl+Shift+S or use Snipping Tool

**Firefox** (same dimensions):
1. Press Ctrl+Shift+M for Responsive Design Mode
2. Set to 1280x800
3. Take screenshot

### Promotional Images (optional but recommended)

| Image | Dimensions | Used by |
|-------|-----------|---------|
| Small promotional tile | 440x280 | Chrome Web Store |
| Large promotional tile | 920x680 | Chrome Web Store |
| Marquee | 1400x560 | Chrome Web Store (featured) |
| Edge promotional | 440x280 | Edge Add-ons |

---

## Submission Checklist

### Edge Add-ons (FREE — do first)
- [ ] Create Microsoft Partner Center account
- [ ] Upload `bhapi-edge.zip`
- [ ] Fill name, description, category
- [ ] Set privacy policy URL: `https://bhapi.ai/legal/privacy`
- [ ] Upload at least 1 screenshot (1280x800)
- [ ] Submit for review

### Firefox AMO (FREE — do second)
- [ ] Create Firefox developer account
- [ ] Upload `bhapi-firefox.zip`
- [ ] Upload `bhapi-firefox-source.zip` (source code)
- [ ] Enter build instructions: `npm install && npm run build`
- [ ] Fill name, description, category
- [ ] Set privacy policy URL
- [ ] Upload at least 1 screenshot
- [ ] Submit for review

### Chrome Web Store ($5 — do third)
- [ ] Create Google Developer account ($5 fee)
- [ ] Upload `bhapi-chrome.zip`
- [ ] Fill name, short description, full description
- [ ] Select category: Education
- [ ] Set privacy policy URL
- [ ] Fill "Single purpose" description
- [ ] Fill permission justifications
- [ ] Complete Privacy Practices declarations
- [ ] Upload at least 1 screenshot (1280x800)
- [ ] Optional: upload promotional tile (440x280)
- [ ] Submit for review

### Safari / Mac App Store ($99/year — do last)
- [ ] Enroll in Apple Developer Program
- [ ] Open Xcode project, set bundle ID and team
- [ ] Archive and upload to App Store Connect
- [ ] Fill app listing (name, description, keywords, category)
- [ ] Set privacy policy URL
- [ ] Upload screenshots
- [ ] Submit for review
