# Parently Launch Checklist

## Current Deployment Status (fill as you go)

- [ ] Frontend live domain confirmed (`https://parently-ai.com`)
- [ ] Backend live domain confirmed
- [ ] Stripe mode confirmed (test/live)
- [ ] Support inbox tested (`support@parently-ai.com`)

## Repo + Build

- [ ] Repository pushed to GitHub as `parently-ai`
- [ ] No secrets committed (`.env`, credentials, tokens)
- [ ] `apps/backend/env.example` and `apps/web/env.example` are current
- [ ] Frontend build passes (`npm run build`)
- [ ] Backend startup passes (`alembic upgrade head && uvicorn ...`)

## Database + Migrations

- [ ] Neon Postgres project created
- [ ] `pgvector` enabled
- [ ] `BACKEND_DATABASE_URL` configured in Railway backend
- [ ] Alembic migrations run successfully in Railway deploy

## Auth + Session

- [ ] Google OAuth credentials created
- [ ] Authorized origins/redirect URIs include `parently-ai.com` and Railway URL
- [ ] Google account chooser verified (always shows account selection)
- [ ] Logged-in backend proxy calls include bearer auth
- [ ] New user onboarding redirect works
- [ ] Returning user dashboard redirect works

## Billing + Entitlements

- [ ] Stripe product created (`Parently Premium`)
- [ ] Stripe monthly price created (`$3/month`)
- [ ] `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, `STRIPE_WEBHOOK_SECRET` configured
- [ ] Webhook endpoint set to `/api/billing/webhook`
- [ ] Webhook events enabled (`checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`)
- [ ] Free user quota exhaustion returns HTTP 402
- [ ] Upgrade flow works for logged-in free users
- [ ] Premium users bypass paywall

## Cron + Background Refresh

- [ ] `CRON_SECRET` configured
- [ ] Daily digest cron endpoint secured and scheduled
- [ ] School source refresh cron endpoint secured and scheduled

## Support + Policies

- [ ] `/support` page deployed and form submit tested
- [ ] `/privacy` page deployed
- [ ] `/terms` page deployed
- [ ] Footer links include support/privacy/terms
- [ ] Support email shown consistently as `support@parently-ai.com`
- [ ] SMTP (Namecheap Private Email or equivalent) configured if contact emails enabled

## PWA + Store Prep

- [ ] `manifest.json` validated
- [ ] Icons present and install flow tested
- [ ] `/.well-known/assetlinks.json` updated with release certificate SHA256
- [ ] PWABuilder/Bubblewrap package generation tested
- [ ] Play Console contact email set to `support@parently-ai.com`

## Pre-Launch Verification

- [ ] Railway backend `/healthz` returns `{"ok": true}`
- [ ] CORS allows custom domain + Railway domain
- [ ] End-to-end happy path verified:
  - login -> onboarding -> source discovery -> digest run -> history
- [ ] Stripe test payments pass in test mode
- [ ] Stripe live keys and live webhook cutover planned before public launch
