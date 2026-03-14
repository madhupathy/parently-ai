# Parently Deployment Guide

This guide productionizes Parently with Railway + Neon using the same hardened pattern used for Panchang AI.

## Actual/Current Values

- Frontend domain (planned): `https://parently-ai.com`
- Support email: `support@parently-ai.com`
- Stripe status: `_set to test or live before launch_`
- Backend public URL: `_set after Railway backend deploy_`
- Frontend public URL: `_set after Railway frontend deploy_`

## 1) Services to Create

- GitHub repo: `parently-ai`
- Railway service 1: backend (`apps/backend`)
- Railway service 2: web (`apps/web`)
- Neon Postgres project with `pgvector`
- Google OAuth Web app credentials
- Stripe product/price (`Parently Premium`, `$3/month`)

## 2) Backend on Railway

- Root directory: `apps/backend`
- Start command:
  - `alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port $PORT`
- Healthcheck path:
  - `/healthz`

### Backend Environment Variables

Set without quotes in Railway Variables:

```env
BACKEND_DATABASE_URL=postgresql://...
NEXTAUTH_SECRET=your-shared-secret
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-1.5-flash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
STRIPE_SECRET_KEY=sk_test_or_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
FRONTEND_APP_URL=https://parently-ai.com
ALLOWED_ORIGINS=https://parently-ai.com,https://<frontend>.up.railway.app,http://localhost:3001
CRON_SECRET=your-cron-secret
SUPPORT_EMAIL=support@parently-ai.com
SMTP_HOST=mail.privateemail.com
SMTP_PORT=587
SMTP_USER=support@parently-ai.com
SMTP_PASSWORD=...
SMTP_FROM=support@parently-ai.com
SMTP_FROM_NAME=Parently
SMTP_SECURE=false
```

## 3) Frontend on Railway

- Root directory: `apps/web`
- Build: `npm install && npm run build`
- Start: `npm run start`

### Frontend Environment Variables

```env
BACKEND_URL=https://<backend>.up.railway.app
NEXTAUTH_SECRET=your-shared-secret
NEXTAUTH_URL=https://parently-ai.com
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
NEXT_PUBLIC_APPLE_AUTH_ENABLED=false
APPLE_CLIENT_ID=
APPLE_CLIENT_SECRET=
```

## 4) Google OAuth (Production-safe)

Authorized JavaScript origins:

- `https://parently-ai.com`
- `https://<frontend>.up.railway.app`
- `http://localhost:3001`

Authorized redirect URIs:

- `https://parently-ai.com/api/auth/callback/google`
- `https://<frontend>.up.railway.app/api/auth/callback/google`
- `http://localhost:3001/api/auth/callback/google`

Parently auth is configured with Google account chooser (`prompt=select_account`).

## 5) Stripe Billing

Create Stripe product and recurring monthly price:

- Product: `Parently Premium`
- Price: `$3/month`

Backend checkout endpoint:

- `POST /api/billing/create-checkout-session`

Webhook endpoint:

- `https://<backend>.up.railway.app/api/billing/webhook`

Subscribe these events:

- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

## 6) Cron Jobs

Cron endpoints require header `X-Cron-Secret`.

- `POST /api/internal/run-daily-digests`
- `POST /api/internal/refresh-school-sources`

## 7) PWA + Store Readiness

- Manifest: `apps/web/public/manifest.json`
- Asset links: `apps/web/public/.well-known/assetlinks.json`
- Update `assetlinks.json` with Play signing certificate before store release.

## 8) Support and Policy Pages

Ensure these pages are deployed and reachable:

- `/support`
- `/privacy`
- `/terms`

Support email for customer communications and receipts/support: `support@parently-ai.com`.
Checkout customer email must always be the authenticated user email.

## Common Deployment Pitfalls

- Railway service does not bind to `$PORT` or `0.0.0.0`
- Google OAuth `redirect_uri_mismatch`
- Missing backend `Authorization: Bearer ...` on proxy calls
- Stripe webhook not configured or wrong signing secret
- `ALLOWED_ORIGINS` missing custom domain and Railway domain
- Modal stacking/z-index issues causing top-stuck dialogs
- Missing `/.well-known/assetlinks.json` for TWA verification
