# Production Launch Checklist — bhapi.ai

**Target:** Go-live on bhapi.ai
**Prerequisites:** All Phase 1 launch blockers complete (SSO, legal, DPIA, consent withdrawal, Stripe script, pen test plan)

---

## 1. OAuth SSO Credentials

### 1.1 Google

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project (or select existing): **Bhapi AI Portal**
3. Navigate to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
4. Application type: **Web application**
5. Name: **Bhapi Portal**
6. Authorized redirect URIs:
   - `https://bhapi.ai/api/v1/auth/oauth/google/callback`
   - `http://localhost:8000/api/v1/auth/oauth/google/callback` (development)
7. Copy **Client ID** and **Client Secret**
8. Navigate to **OAuth consent screen**:
   - App name: **Bhapi**
   - User support email: support@bhapi.ai
   - Authorized domains: `bhapi.ai`
   - Developer contact: support@bhapi.ai
   - Scopes: `openid`, `email`, `profile`
9. Submit for verification (required for >100 users)

**Env vars:**
```
OAUTH_GOOGLE_CLIENT_ID=<client-id>.apps.googleusercontent.com
OAUTH_GOOGLE_CLIENT_SECRET=GOCSPX-...
```

### 1.2 Microsoft (Azure AD)

1. Go to [Azure Portal → App registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. **New registration**:
   - Name: **Bhapi AI Portal**
   - Supported account types: **Accounts in any organizational directory and personal Microsoft accounts**
   - Redirect URI: **Web** → `https://bhapi.ai/api/v1/auth/oauth/microsoft/callback`
3. Note the **Application (client) ID**
4. Navigate to **Certificates & secrets → New client secret**
   - Description: **Bhapi Production**
   - Expiry: 24 months
   - Copy the **Value** immediately (shown once)
5. Navigate to **API permissions**:
   - Microsoft Graph → Delegated → `openid`, `email`, `profile`
   - Click **Grant admin consent**

**Env vars:**
```
OAUTH_MICROSOFT_CLIENT_ID=<application-id>
OAUTH_MICROSOFT_CLIENT_SECRET=<secret-value>
```

### 1.3 Apple

1. Go to [Apple Developer → Certificates, Identifiers & Profiles](https://developer.apple.com/account/resources/identifiers/list)
2. **Register App ID**:
   - Description: **Bhapi AI Portal**
   - Bundle ID: `ai.bhapi.portal`
   - Enable **Sign In with Apple**
3. **Register Services ID**:
   - Description: **Bhapi Web Auth**
   - Identifier: `ai.bhapi.auth`
   - Enable **Sign In with Apple** → Configure:
     - Domains: `bhapi.ai`
     - Return URL: `https://bhapi.ai/api/v1/auth/oauth/apple/callback`
4. **Create Key**:
   - Key name: **Bhapi Sign In**
   - Enable **Sign In with Apple**
   - Download the `.p8` key file (shown once)
   - Note the **Key ID**
5. Generate client secret (Apple uses JWT-based secrets):
   - Use the Team ID, Key ID, and `.p8` file to generate a JWT
   - See [Apple docs](https://developer.apple.com/documentation/sign_in_with_apple/generate_and_validate_tokens)

**Env vars:**
```
OAUTH_APPLE_CLIENT_ID=ai.bhapi.auth
OAUTH_APPLE_CLIENT_SECRET=<generated-jwt>
OAUTH_APPLE_TEAM_ID=<team-id>
OAUTH_APPLE_KEY_ID=<key-id>
```

---

## 2. Stripe Setup

### 2.1 Create Products and Prices

In [Stripe Dashboard → Products](https://dashboard.stripe.com/products):

| Product | Monthly Price | Annual Price |
|---------|--------------|--------------|
| Bhapi Family | $9.99/mo | $99.99/yr |
| Bhapi School | $29.99/mo | $299.99/yr |
| Bhapi Club | $19.99/mo | $199.99/yr |

For each product:
1. Click **Add product**
2. Set name (e.g., "Bhapi Family Plan")
3. Add **Recurring** price for monthly
4. Add **Recurring** price for annual
5. Copy the **Price ID** (starts with `price_`)

### 2.2 Configure Webhook

1. Go to [Stripe Dashboard → Webhooks](https://dashboard.stripe.com/webhooks)
2. **Add endpoint**:
   - URL: `https://bhapi.ai/api/v1/billing/webhooks`
   - Events to listen for:
     - `checkout.session.completed`
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.paid`
     - `invoice.payment_failed`
3. Copy the **Signing secret** (starts with `whsec_`)

### 2.3 Configure Billing Portal

1. Go to [Stripe Dashboard → Settings → Billing → Customer portal](https://dashboard.stripe.com/settings/billing/portal)
2. Enable:
   - Update payment method
   - Cancel subscription
   - View invoices
3. Set return URL: `https://bhapi.ai/settings`

### 2.4 Run Verification Script

```bash
STRIPE_SECRET_KEY=sk_test_... python scripts/stripe_live_test.py
```

Review all [PASS]/[FAIL] output before proceeding to live keys.

**Env vars:**
```
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
```

Optional per-plan price IDs (for checkout):
```
STRIPE_PRICE_FAMILY_MONTHLY=price_...
STRIPE_PRICE_FAMILY_ANNUAL=price_...
STRIPE_PRICE_SCHOOL_MONTHLY=price_...
STRIPE_PRICE_SCHOOL_ANNUAL=price_...
STRIPE_PRICE_CLUB_MONTHLY=price_...
STRIPE_PRICE_CLUB_ANNUAL=price_...
```

---

## 3. SendGrid Email

1. Go to [SendGrid → Settings → API Keys](https://app.sendgrid.com/settings/api_keys)
2. **Create API Key**:
   - Name: **Bhapi Production**
   - Permissions: **Restricted Access** → Mail Send: Full Access
3. **Verify sender** (Settings → Sender Authentication):
   - Domain: `bhapi.ai`
   - Set up DNS records (CNAME for DKIM/SPF)
4. Test with: `SENDGRID_API_KEY=SG... python -c "from src.email.service import send_email; ..."`

**Env var:**
```
SENDGRID_API_KEY=SG....
```

---

## 4. DPO Review

- [ ] DPO reviews `docs/compliance/dpia.md`
- [ ] DPO signs off on data processing activities
- [ ] DPO email (dpo@bhapi.ai) is active and monitored
- [ ] Privacy policy at `/legal/privacy` reviewed by legal counsel
- [ ] Terms of service at `/legal/terms` reviewed by legal counsel
- [ ] Sign-off recorded in DPIA document (Section 9.3)

---

## 5. Penetration Test

- [ ] Staging environment deployed at `staging.bhapi.ai`
- [ ] `docs/security/pentest-plan.md` sent to CREST-certified provider
- [ ] NDA and Rules of Engagement signed
- [ ] Test accounts provisioned on staging
- [ ] 2-week engagement scheduled
- [ ] Critical findings remediated before go-live
- [ ] Re-test confirms fixes

---

## 6. Render Production Deploy

### 6.1 Pre-deploy Checks

```bash
# Verify Docker builds successfully
docker compose build

# Run full test suite
pytest tests/ -v
cd portal && npx tsc --noEmit && npx vitest run

# Verify render.yaml is valid
cat render.yaml  # Review all env vars listed
```

### 6.2 Deploy Steps

1. Go to [Render Dashboard](https://dashboard.render.com)
2. **New → Blueprint** → Connect `mick-e/bhapi-ai-portal` repo
3. Render auto-detects `render.yaml` and provisions:
   - `bhapi-core-api` (web service)
   - `bhapi-jobs` (cron service)
   - `bhapi-db` (PostgreSQL 16)
4. **Set `sync: false` env vars** in Render dashboard:
   - All OAuth credentials (see Section 1)
   - All Stripe credentials (see Section 2)
   - `SENDGRID_API_KEY` (see Section 3)
   - `GCP_PROJECT_ID` (if using Cloud KMS)
5. **Run Alembic migrations** (one-time, via Render shell):
   ```bash
   alembic upgrade head
   ```
6. Verify health: `curl https://bhapi.ai/health`
7. Verify legal pages: `curl https://bhapi.ai/legal/privacy`
8. Verify API docs: `curl https://bhapi.ai/docs`

### 6.3 Post-deploy Verification

```bash
# Health check
curl https://bhapi.ai/health

# Legal pages accessible
curl -s https://bhapi.ai/legal/privacy | head -5
curl -s https://bhapi.ai/legal/terms | head -5

# Auth endpoints
curl https://bhapi.ai/api/v1/auth/oauth/google/authorize

# Swagger docs
curl -s https://bhapi.ai/openapi.json | python -m json.tool | head -20
```

---

## 7. DNS Configuration

1. Go to your domain registrar (for `bhapi.ai`)
2. Add DNS records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| CNAME | `@` or `bhapi.ai` | `<render-service>.onrender.com` | 300 |
| CNAME | `www` | `<render-service>.onrender.com` | 300 |
| CNAME | `staging` | `<staging-service>.onrender.com` | 300 |

3. In Render dashboard → bhapi-core-api → Settings → Custom Domains:
   - Add `bhapi.ai`
   - Add `www.bhapi.ai`
4. Render auto-provisions TLS certificates via Let's Encrypt
5. Verify: `curl -I https://bhapi.ai` (should show 200 with HSTS header)

---

## 8. Browser Extension Submission

### 8.1 Build

```bash
cd extension
npm install
npm run build     # Outputs to extension/dist/
npm run typecheck  # Verify no TS errors
```

### 8.2 Chrome Web Store

1. Go to [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
2. Pay one-time $5 developer fee (if not already)
3. **Add new item** → Upload `extension/dist/` as ZIP
4. Fill in listing:
   - Name: **Bhapi — AI Safety Monitor**
   - Summary: Monitor children's AI tool usage with real-time safety alerts
   - Category: **Productivity**
   - Language: English
   - Screenshots: Dashboard, alert notification, popup (at least 1 screenshot, 1280x800)
   - Icon: Use `extension/icons/icon-128.png`
5. Privacy practices:
   - Single purpose: "Monitors AI platform usage for child safety"
   - Permissions justification:
     - `tabs`: Detect when user navigates to AI platforms
     - `activeTab`: Read AI interaction content on active tab
     - `storage`: Store user preferences and auth token
   - Data use: Certify compliance with Chrome Web Store policies
   - Privacy policy URL: `https://bhapi.ai/legal/privacy`
6. Submit for review (typically 1-3 business days)

### 8.3 Firefox Add-ons

1. Go to [Firefox Add-on Developer Hub](https://addons.mozilla.org/developers/)
2. **Submit a New Add-on** → Upload `extension/dist/` as ZIP
3. Choose: **On this site** (listed on AMO)
4. Fill in listing details (same as Chrome)
5. Source code: Upload full `extension/` directory (required for review if code is bundled)
6. Submit for review (typically 1-5 business days)

---

## Pre-Launch Final Checklist

- [ ] **All tests pass:** `pytest tests/ -v` (566+) and `cd portal && npx vitest run` (59+)
- [ ] **Docker builds:** `docker compose build` succeeds
- [ ] **TypeScript clean:** `cd portal && npx tsc --noEmit`
- [ ] **OAuth configured:** Google, Microsoft, Apple credentials set in Render
- [ ] **Stripe live:** Products, prices, webhook, portal configured
- [ ] **Stripe verified:** `scripts/stripe_live_test.py` all [PASS]
- [ ] **SendGrid configured:** API key set, domain verified
- [ ] **DPO sign-off:** DPIA reviewed and signed
- [ ] **Pen test:** Critical/high findings remediated
- [ ] **DNS live:** `bhapi.ai` resolves to Render service
- [ ] **TLS active:** `https://bhapi.ai` serves valid certificate
- [ ] **Health check:** `/health` returns `{"status": "healthy"}`
- [ ] **Legal pages:** `/legal/privacy` and `/legal/terms` accessible
- [ ] **Extension submitted:** Chrome Web Store and Firefox Add-ons
- [ ] **Monitoring:** Render alerts configured for downtime/errors

---

*This checklist should be worked through in order. Items 1-5 can proceed in parallel. Items 6-7 require all credentials to be ready. Item 8 can proceed independently.*
