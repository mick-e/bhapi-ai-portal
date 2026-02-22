# Render Deployment Guide — Bhapi AI Portal

## Quick Start

1. Push repo to GitHub
2. Go to https://dashboard.render.com
3. Click **New** → **Blueprint** → select the repo
4. Render reads `render.yaml` and provisions everything automatically
5. Set the manual env vars (Stripe, SendGrid) in the dashboard

## What Gets Created

| Resource | Type | Plan | Region |
|----------|------|------|--------|
| bhapi-core-api | Web Service (Docker) | Starter | Frankfurt |
| bhapi-db | PostgreSQL 16 | Starter | Frankfurt |

## Environment Variables

### Auto-configured
- `DATABASE_URL` — injected from the Render PostgreSQL instance
- `SECRET_KEY` — auto-generated secure random value
- `ENVIRONMENT` — set to `production`

### Manual (set in Render dashboard)
- `STRIPE_SECRET_KEY` — from Stripe dashboard
- `STRIPE_WEBHOOK_SECRET` — from Stripe webhook setup
- `SENDGRID_API_KEY` — from SendGrid dashboard

### Redis (optional)
Redis is optional — the app degrades gracefully without it.
For MVP, leave `REDIS_URL` empty. Add Render Redis ($7/mo) when needed for rate limiting and caching.

## Post-Deploy Steps

1. **Run migrations**: Use Render Shell or connect to the service:
   ```bash
   # In Render Shell (Web Service → Shell tab)
   alembic upgrade head
   ```

2. **Set up Stripe webhook**:
   - URL: `https://bhapi-core-api.onrender.com/api/v1/billing/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.*`, `invoice.*`

3. **Custom domain**:
   - Add `bhapi.ai` in Render dashboard → Settings → Custom Domains
   - Update DNS: CNAME `bhapi.ai` → `bhapi-core-api.onrender.com`

4. **CORS origins**: Update `src/main.py` production origins to include `https://bhapi.ai`

## Database URL Format

Render provides `postgres://` URLs. The app's `config.py` auto-converts to `postgresql+asyncpg://` for asyncpg compatibility.

## Monitoring

- Health check: `GET /health/live` (configured in render.yaml)
- Full health: `GET /health` (returns DB + Redis status)
- Logs: Render dashboard → Logs tab
- Metrics: Render dashboard → Metrics tab

## Cost Estimate (MVP)

| Resource | Monthly Cost |
|----------|-------------|
| Web Service (Starter) | $7 |
| PostgreSQL (Starter) | $7 |
| **Total** | **$14/mo** |

Add Redis when needed: +$7/mo = $21/mo total.
