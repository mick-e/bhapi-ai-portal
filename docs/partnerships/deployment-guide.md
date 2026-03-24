# Bhapi Deployment Guide for Schools and Districts

This guide covers technical deployment of the Bhapi platform at a school or district level. Designed for IT administrators, network engineers, and managed service providers deploying on behalf of schools.

**Estimated deployment time:** 2–4 hours for a single school. 1–3 days for a district rollout.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Chrome Extension Deployment via Google Admin Console](#chrome-extension-deployment)
3. [SSO Setup — Google Workspace](#sso-google-workspace)
4. [SSO Setup — Microsoft Entra ID (Azure AD)](#sso-microsoft-entra)
5. [SIS Sync — Clever](#sis-sync-clever)
6. [SIS Sync — ClassLink](#sis-sync-classlink)
7. [Network Requirements — Domains to Whitelist](#network-requirements)
8. [Rollout Phases](#rollout-phases)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting deployment, ensure you have:

- [ ] An active Bhapi School or District account (contact sales@bhapi.ai if not yet provisioned)
- [ ] Your Bhapi Organization ID (found in Settings → Organization)
- [ ] Google Workspace Admin Console access OR Microsoft Entra admin access
- [ ] Clever or ClassLink admin access (for SIS sync)
- [ ] A list of IP ranges / DNS filtering rules in use on your school network
- [ ] Chrome Browser Management enabled in your Google Admin Console (for managed Chromebooks/Chrome browsers)

---

## Chrome Extension Deployment

The Bhapi browser extension (Manifest V3) monitors student AI tool usage on Chrome. For school-managed devices, deploy via Google Admin Console for a silent, zero-touch installation.

### Step 1 — Obtain the Extension ID

The Bhapi Chrome extension is available on the Chrome Web Store:
- **Extension ID:** `bhapi-school-monitor` (full ID provided in your welcome email)
- **Chrome Web Store URL:** `https://chrome.google.com/webstore/detail/bhapi-ai-safety/<extension-id>`

For schools using allowlist-only Chrome policies, the extension must be on your approved list before deployment.

### Step 2 — Deploy via Google Admin Console

1. Sign in to [admin.google.com](https://admin.google.com)
2. Go to **Devices → Chrome → Apps and extensions**
3. Select the target Organizational Unit (OU) — e.g., Students, or a specific grade-level OU
4. Click the **+** button → **Add from Chrome Web Store**
5. Search for "Bhapi AI Safety" or paste the extension ID
6. Set installation policy to **Force install**
7. Under **Policy for extensions**, paste the following JSON (replace with your Organization ID):

```json
{
  "organizationId": {
    "Value": "YOUR_BHAPI_ORG_ID"
  },
  "monitoringEnabled": {
    "Value": true
  },
  "reportingEndpoint": {
    "Value": "https://bhapi.ai/api/v1/capture"
  },
  "platforms": {
    "Value": ["chatgpt", "gemini", "copilot", "claude", "grok", "character_ai", "perplexity", "poe"]
  }
}
```

8. Click **Save**
9. The extension will be silently installed on all managed Chrome browsers in the OU within 15–30 minutes

### Step 3 — Verify Installation

After the policy propagates:
1. On a student device, navigate to `chrome://extensions` — Bhapi AI Safety should appear as an installed extension with the managed badge
2. In the Bhapi admin dashboard, go to **Settings → Extension Status** — enrolled devices will appear within 60 minutes of first use

### Firefox and Safari

- **Firefox:** Extension is available in the Firefox Add-ons store. Firefox enterprise deployment uses `policies.json` (details on request)
- **Safari:** Available via App Store. School deployment requires Apple School Manager + Managed Apple IDs

---

## SSO Setup — Google Workspace

Bhapi supports Google Workspace SSO via OpenID Connect (OIDC). Students and staff sign in with their school Google account — no separate Bhapi passwords required.

### Step 1 — Create an OAuth 2.0 Client in Google Cloud Console

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Select or create a project for your school (e.g., "Bhapi SSO")
3. Navigate to **APIs & Services → Credentials**
4. Click **Create Credentials → OAuth client ID**
5. Application type: **Web application**
6. Name: "Bhapi School Portal"
7. Authorized redirect URIs — add both:
   - `https://bhapi.ai/api/v1/integrations/google/callback`
   - `https://bhapi.ai/auth/callback` (fallback)
8. Click **Create** — note your **Client ID** and **Client Secret**

### Step 2 — Configure Bhapi

1. Sign in to [bhapi.ai](https://bhapi.ai) as your Organization Admin
2. Go to **Settings → Integrations → Google Workspace SSO**
3. Enter your Client ID and Client Secret
4. Set **Allowed Domain** to your school's Google Workspace domain (e.g., `students.lincolnk12.edu`)
5. Toggle **Enforce SSO** to require Google login for all members
6. Click **Save and Test** — a test login window will open

### Step 3 — Enable in Google Admin Console (optional — restrict OAuth access)

To ensure only students in your domain can trigger the OAuth flow:
1. In Google Admin Console → **Security → API controls → App access control**
2. Add Bhapi as a trusted app using the Client ID from Step 1
3. Set access level to your Students OU

### Auto-Provisioning

When Google SSO is enabled, students who sign in for the first time are automatically provisioned as members of your Bhapi organization. Parent accounts must still be created manually (or via SIS sync for guardian data).

---

## SSO Setup — Microsoft Entra ID (Azure AD)

For schools using Microsoft 365 and managed Windows devices.

### Step 1 — Register an Application in Entra ID

1. Sign in to [portal.azure.com](https://portal.azure.com) as a Global Administrator
2. Navigate to **Azure Active Directory → App registrations → New registration**
3. Name: "Bhapi AI Safety Portal"
4. Supported account types: **Accounts in this organizational directory only**
5. Redirect URI: `https://bhapi.ai/api/v1/integrations/entra/callback`
6. Click **Register**

### Step 2 — Configure Permissions

1. In your new app registration, go to **API permissions**
2. Click **Add a permission → Microsoft Graph → Delegated permissions**
3. Add: `openid`, `profile`, `email`, `User.Read`
4. Click **Grant admin consent for [Your Organization]**

### Step 3 — Create a Client Secret

1. Go to **Certificates & secrets → New client secret**
2. Description: "Bhapi SSO Secret"
3. Expiry: 24 months (recommended — set a calendar reminder to rotate)
4. Note the **Value** immediately — it is only shown once

### Step 4 — Configure Bhapi

1. In Bhapi, go to **Settings → Integrations → Microsoft Entra SSO**
2. Enter:
   - **Tenant ID** (from app registration overview)
   - **Client ID** (Application ID from overview)
   - **Client Secret** (from Step 3)
3. Set **Allowed Tenant** to enforce your school's domain
4. Click **Save and Test**

### Step 5 — Deploy via Microsoft Endpoint Manager (optional)

For automatic silent sign-in on managed Windows devices, configure Enterprise SSO via Intune:
1. In Intune → **Devices → Configuration → Create → Windows 10 → Settings Catalog**
2. Add the Microsoft SSO Extension settings pointing to your Tenant ID
3. Assign to your Students device group

---

## SIS Sync — Clever

Clever automatically syncs your student roster, class assignments, and guardian contacts into Bhapi — eliminating manual data entry and keeping your member list current.

### Prerequisites
- Clever District Admin access
- Bhapi Reseller or School account with SIS sync enabled (contact sales if not included in your plan)

### Step 1 — Add Bhapi in Clever Library

1. Sign in to [clever.com](https://clever.com) as District Admin
2. Go to **Applications → Library**
3. Search for "Bhapi AI Safety"
4. Click **Request Access** — the Bhapi team will approve within 1 business day

### Step 2 — Configure Data Sync

Once approved, Clever will prompt you to configure the data share:
1. Select your district
2. Data to share with Bhapi:
   - **Students** — required (name, grade, date of birth)
   - **Teachers** — optional (for staff accounts)
   - **Sections/Classes** — optional (for class-based group creation)
   - **Guardians** — recommended (for automatic parent account creation)
3. Click **Authorize**

### Step 3 — Verify in Bhapi

1. In Bhapi, go to **Settings → Integrations → Clever**
2. Click **Connect to Clever** — you will be redirected to Clever to complete OAuth
3. After connecting, click **Sync Now** to pull your initial roster
4. Verify student count matches your Clever roster in **Members → All Members**

### Ongoing Sync

Clever syncs automatically every night at 2:00 AM local time. Roster changes (new enrollments, grade changes, withdrawals) are reflected in Bhapi by the next morning.

---

## SIS Sync — ClassLink

ClassLink OneRoster integration follows a similar pattern to Clever.

### Step 1 — Obtain ClassLink Credentials

1. Sign in to ClassLink LaunchPad as District Admin
2. Go to **App Library → Manage → API**
3. Generate API credentials for Bhapi (Client ID + Client Secret)
4. Note the **Tenant URL** (e.g., `https://launchpad.classlink.com/YOUR_DISTRICT`)

### Step 2 — Configure Bhapi

1. In Bhapi, go to **Settings → Integrations → ClassLink**
2. Enter:
   - Tenant URL
   - Client ID
   - Client Secret
3. Select the data to sync (students, guardians, classes)
4. Click **Save and Sync**

### Step 3 — Verify

Verify the member count in **Members → All Members**. ClassLink syncs automatically every 6 hours.

---

## Network Requirements

Ensure the following domains are reachable from school networks and student devices. These must not be blocked by content filters or DNS policies.

### Required Domains (Core Functionality)

| Domain | Purpose | Port |
|--------|---------|------|
| `bhapi.ai` | Main portal and API | 443 (HTTPS) |
| `api.bhapi.ai` | Backend API endpoint | 443 (HTTPS) |
| `realtime.bhapi.ai` | WebSocket real-time alerts | 443 (WSS) |
| `cdn.bhapi.ai` | Static assets (JS, CSS, images) | 443 (HTTPS) |

### Required Domains (Integrations)

| Domain | Purpose | Notes |
|--------|---------|-------|
| `api.clever.com` | Clever SIS sync | Only if using Clever |
| `launchpad.classlink.com` | ClassLink SIS sync | Only if using ClassLink |
| `accounts.google.com` | Google SSO | Only if using Google SSO |
| `login.microsoftonline.com` | Entra ID SSO | Only if using Microsoft SSO |

### Extension Reporting

The Chrome extension sends captured events to:
- `https://bhapi.ai/api/v1/capture` — event ingestion endpoint

This endpoint must be reachable from all student devices (including personal devices if BYOD is in scope).

### DNS Filtering Notes

If your school uses a DNS filter (e.g., GoGuardian, Securly, Bark), ensure `bhapi.ai` and its subdomains are in the **allow list**. Some filters may categorize new domains as uncategorized until manually approved.

---

## Rollout Phases

A phased rollout minimizes disruption and allows for feedback before school-wide deployment.

### Phase 1 — Pilot (Weeks 1–2)

**Scope:** 1–2 classes or a single grade level (50–100 students)

**Goals:**
- Validate SSO and SIS sync are working correctly
- Confirm the extension installs and reports correctly
- Test parent notification flow with 2–3 volunteer families
- Identify any network or device-specific issues

**Checklist:**
- [ ] SSO configured and tested
- [ ] Extension deployed to pilot OU in Google Admin Console
- [ ] SIS sync completed — pilot students visible in Bhapi
- [ ] Parent accounts created and email verified for pilot families
- [ ] At least 1 test alert triggered and received by a parent
- [ ] IT admin sign-off from at least one school building

---

### Phase 2 — Grade Level (Weeks 3–4)

**Scope:** Full grade or department (200–500 students)

**Goals:**
- Scale pilot learnings to a larger group
- Communicate to parents via principal or counselor email
- Establish weekly review cadence for the safeguarding team

**Parent Communication Template:**

> *Dear [School Name] Families,*
>
> *We are rolling out Bhapi AI Safety to help support responsible AI use among our students. Bhapi monitors AI tool activity on school devices and can alert you when concerning content is detected. You will receive an invitation to create your parent account via email. [Principal Name]*

---

### Phase 3 — School-Wide (Weeks 5–6)

**Scope:** All students in the school (500–2,000 students)

**Goals:**
- Complete extension deployment to all student OUs
- Parent onboarding completion rate >70%
- Safeguarding team trained on alert triage and reporting
- AI usage policy reviewed and updated to reference Bhapi

**Training checklist:**
- [ ] School principal / head briefed (30-min session)
- [ ] Safeguarding lead / DSL trained on Bhapi dashboard (60-min session)
- [ ] IT admin familiar with extension management and user provisioning
- [ ] Parent FAQ published on school website

---

### Phase 4 — District-Wide (Months 2–3)

**Scope:** All schools in the district

**Goals:**
- Replicate Phase 1–3 at each school with building-level IT leads
- Consolidate reporting at district level (Bhapi District Dashboard)
- Establish district AI policy using Bhapi's governance templates
- Quarterly review meeting with Bhapi partner success manager

**District-specific features:**
- Cross-school analytics dashboard
- District-level AI policy templates (Ohio HB 96 template available)
- Centralized parent communication portal
- District admin single sign-on with role-based access per school

---

## Troubleshooting

### Extension not appearing on student devices

- **Check OU assignment** — ensure the student's device is in the correct OU in Google Admin Console
- **Check policy propagation** — allow up to 30 minutes for Chrome policy to sync
- **Force policy refresh** — on the student device, run `chrome://policy` and click "Reload policies"
- **Verify Chrome version** — Bhapi extension requires Chrome 108+

### Students not appearing in Bhapi after SIS sync

- **Clever:** Check that the data share is authorized and the Bhapi app shows as "Active" in Clever
- **ClassLink:** Verify API credentials have not expired (ClassLink credentials expire annually)
- **Manual sync:** In Bhapi Settings → Integrations, click "Sync Now" to trigger an immediate sync

### SSO login failing

- **Google:** Verify the redirect URI in Google Cloud Console exactly matches `https://bhapi.ai/api/v1/integrations/google/callback`
- **Entra:** Check that admin consent has been granted for the required permissions
- **Both:** Ensure the Allowed Domain in Bhapi Settings matches the student email domain exactly

### Parent not receiving alert emails

- **Check spam folder** — alerts@bhapi.ai may hit spam for new recipients
- **Verify email consent** — COPPA 2026 requires explicit consent for email communication to parents of under-13 students; check the consent status in the parent's profile
- **Check alert thresholds** — by default, alerts are sent for High and Critical severity only; adjust in Settings → Alerts → Thresholds

---

## Support

- **Partner support:** [partners@bhapi.ai](mailto:partners@bhapi.ai)
- **IT admin support:** [support@bhapi.ai](mailto:support@bhapi.ai)
- **Documentation:** [bhapi.ai/docs](https://bhapi.ai/docs)
- **Status page:** [status.bhapi.ai](https://status.bhapi.ai)

For urgent deployment blockers during a school rollout, Reseller partners may contact their partner success manager directly via the partner Slack channel.

---

*Last updated: 2026-03-24 | Version 1.0 | Contact: support@bhapi.ai*
