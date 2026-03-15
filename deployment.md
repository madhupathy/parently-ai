# Parently AI Production Deployment Checklist

Use this as the single checklist for production deployment and launch readiness.

## Pre-deployment checklist

- [ ] Production frontend domain is `https://parently-ai.com`
- [ ] Backend public URL confirmed as `https://<backend>.up.railway.app`
- [ ] Frontend Railway URL confirmed as `https://<frontend>.up.railway.app`
- [ ] Stripe mode selected (`test` or `live`)
- [ ] Support mailbox validated (`support@parently-ai.com`)
- [ ] Repository is free of committed secrets

## Neon Postgres setup

- [ ] Neon project and database created
- [ ] `pgvector` enabled: `CREATE EXTENSION IF NOT EXISTS vector;`
- [ ] Production connection string set in `BACKEND_DATABASE_URL`
- [ ] Access policies and credentials reviewed
- [ ] Alembic migration succeeds during backend deploy
- [ ] Empty DB migration chain validated:
  - [ ] `alembic downgrade base`
  - [ ] `alembic upgrade head`

## Railway backend deployment

- [ ] Service root directory: `apps/backend`
- [ ] Start command: `alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port $PORT`
- [ ] Health check endpoint returns success: `/healthz`
- [ ] Backend variables configured:
  - [ ] `BACKEND_DATABASE_URL`
  - [ ] `NEXTAUTH_SECRET`
  - [ ] `FRONTEND_APP_URL=https://parently-ai.com`
  - [ ] `ALLOWED_ORIGINS` includes `https://parently-ai.com` and active Railway frontend domain
  - [ ] `CRON_SECRET`
  - [ ] `SUPPORT_EMAIL`
  - [ ] `GEMINI_API_KEY`
  - [ ] `GEMINI_MODEL`
  - [ ] `OPENAI_API_KEY` (optional)
  - [ ] `OPENAI_MODEL` (optional)
  - [ ] `STRIPE_SECRET_KEY`
  - [ ] `STRIPE_PRICE_ID`
  - [ ] `STRIPE_WEBHOOK_SECRET`
  - [ ] `SMTP_HOST`
  - [ ] `SMTP_PORT`
  - [ ] `SMTP_USER`
  - [ ] `SMTP_PASSWORD`
  - [ ] `SMTP_FROM`
  - [ ] `SMTP_FROM_NAME`
  - [ ] `SMTP_SECURE`

## Railway frontend deployment

- [ ] Service root directory: `apps/web`
- [ ] Build/start pipeline completes successfully
- [ ] Frontend variables configured:
  - [ ] `BACKEND_URL=https://<backend>.up.railway.app` (replace placeholder)
  - [ ] `NEXTAUTH_SECRET` (must match backend)
  - [ ] `NEXTAUTH_URL=https://parently-ai.com`
  - [ ] `AUTH_TRUST_HOST=true`
  - [ ] `GOOGLE_CLIENT_ID`
  - [ ] `GOOGLE_CLIENT_SECRET`
  - [ ] `NEXT_PUBLIC_APPLE_AUTH_ENABLED`
  - [ ] `APPLE_CLIENT_ID` (if enabled)
  - [ ] `APPLE_CLIENT_SECRET` (if enabled)
- [ ] Production domain is serving frontend traffic

## Google OAuth setup

- [ ] OAuth web application credentials created
- [ ] Authorized JavaScript origins include:
  - [ ] `https://parently-ai.com`
  - [ ] `https://<frontend>.up.railway.app`
  - [ ] `http://localhost:3001`
- [ ] Authorized redirect URIs include:
  - [ ] `https://parently-ai.com/api/auth/callback/google`
  - [ ] `https://<frontend>.up.railway.app/api/auth/callback/google`
  - [ ] `http://localhost:3001/api/auth/callback/google`
- [ ] Production Google login flow validated

## Stripe setup

- [ ] Product and monthly recurring price created (`Parently Premium`, `$3/month`)
- [ ] Webhook endpoint configured: `https://<backend>.up.railway.app/api/billing/webhook`
- [ ] Webhook events enabled:
  - [ ] `checkout.session.completed`
  - [ ] `customer.subscription.updated`
  - [ ] `customer.subscription.deleted`
- [ ] Checkout and entitlement updates verified end-to-end

## Cron jobs

- [ ] `POST /api/internal/run-daily-digests` is scheduled
- [ ] `POST /api/internal/refresh-school-sources` is scheduled
- [ ] `X-Cron-Secret` header is configured with `CRON_SECRET`
- [ ] Scheduled execution appears in logs

## Core product verification

- [ ] User sign-in works
- [ ] Onboarding completes successfully
- [ ] School discovery returns valid source results
- [ ] Setup status endpoint is healthy: `GET /api/setup/status`
- [ ] Manual digest generation succeeds
- [ ] Notification read/unread flows work
- [ ] Billing upgrade flow succeeds
- [ ] Free-plan limits enforce HTTP `402` when expected

## Continuous migration safety

- [ ] GitHub Actions migration check is enabled (`.github/workflows/migrations.yml`)
- [ ] CI migration job passes against fresh Postgres before release

## Domain / DNS / SSL

- [ ] `https://parently-ai.com` points to frontend service
- [ ] SSL certificate is active and valid
- [ ] `NEXTAUTH_URL` set to `https://parently-ai.com`
- [ ] `FRONTEND_APP_URL` set to `https://parently-ai.com`
- [ ] `ALLOWED_ORIGINS` includes production + active Railway frontend domains

## PWA / app store readiness

- [ ] `manifest.json` and required icons are valid
- [ ] `/.well-known/assetlinks.json` exists and has release cert fingerprint
- [ ] Install prompt verified on supported browsers
- [ ] `/support`, `/privacy`, and `/terms` are reachable
- [ ] Store listing assets and compliance docs are prepared

## Launch readiness

- [ ] Backend logs show no critical auth, billing, or DB errors
- [ ] Frontend logs show no critical runtime errors
- [ ] Full production smoke test passes on `https://parently-ai.com`
- [ ] Rollback plan documented
- [ ] Final go/no-go decision recorded

## Common pitfalls recheck

- [ ] `NEXTAUTH_SECRET` matches in frontend and backend
- [ ] `NEXTAUTH_URL` is not blank
- [ ] `AUTH_TRUST_HOST=true` is set on Railway frontend
- [ ] Stripe secret key, price ID, and webhook secret are all from the same mode
- [ ] `ALLOWED_ORIGINS` includes the actual frontend domain
- [ ] Backend binds to `0.0.0.0:$PORT`
