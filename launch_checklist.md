# Parently AI - Launch + Setup Checklist

Use this as the end-to-end deployment and launch checklist for Parently AI as a production SaaS.

## Current Deployment Snapshot

- [ ] Frontend production domain confirmed (`https://parently-ai.com`)
- [ ] Backend production URL confirmed (`https://<backend>.up.railway.app`)
- [ ] Stripe mode confirmed (`test` or `live`)
- [ ] Support inbox tested (`support@parently-ai.com`)

---

## 1) Project + Repository

- [x] GitHub repository created: `madhupathy/parently-ai`
- [x] Main branch pushed
- [ ] Branch protection enabled on `main`
- [ ] Required reviewers configured
- [ ] Secrets scanning enabled in GitHub
- [ ] No secrets committed (`.env`, credentials, tokens)
- [ ] `apps/backend/env.example` and `apps/web/env.example` are current

### Build Verification

- [ ] Frontend build passes (`npm run build`)
- [ ] Backend startup passes (`alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port $PORT`)

---

## 2) Neon Postgres Setup

- [ ] Neon project created
- [ ] Database created
- [ ] Connection string copied (`postgresql://...`)
- [ ] `pgvector` extension enabled:
  - [ ] `CREATE EXTENSION IF NOT EXISTS vector;`
- [ ] `BACKEND_DATABASE_URL` set in Railway backend variables
- [ ] DB access restricted to required environments only
- [ ] Alembic migrations run successfully in Railway deploy

---

## 3) Railway Backend Deployment (`apps/backend`)

- [ ] Railway project created
- [ ] Backend service created from GitHub repo
- [ ] Backend root directory set to `apps/backend`
- [ ] Start command set:
  - [ ] `alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port $PORT`
- [ ] Healthcheck path set to:
  - [ ] `/healthz`
- [ ] First deploy succeeded
- [ ] Healthcheck returns:
  - [ ] `{"ok": true}`

### Backend Environment Variables

- [ ] `BACKEND_DATABASE_URL`
- [ ] `NEXTAUTH_SECRET`
- [ ] `GEMINI_API_KEY`
- [ ] `GEMINI_MODEL=gemini-1.5-flash`
- [ ] `OPENAI_API_KEY` (optional)
- [ ] `OPENAI_MODEL=gpt-4o-mini`
- [ ] `STRIPE_SECRET_KEY`
- [ ] `STRIPE_WEBHOOK_SECRET`
- [ ] `STRIPE_PRICE_ID`
- [ ] `FRONTEND_APP_URL`
- [ ] `ALLOWED_ORIGINS` (custom domain + Railway domain + localhost for dev)
- [ ] `CRON_SECRET`
- [ ] `SUPPORT_EMAIL=support@parently-ai.com`
- [ ] `SMTP_HOST`
- [ ] `SMTP_PORT`
- [ ] `SMTP_USER`
- [ ] `SMTP_PASSWORD`
- [ ] `SMTP_FROM`
- [ ] `SMTP_FROM_NAME`
- [ ] `SMTP_SECURE`

---

## 4) Railway Frontend Deployment (`apps/web`)

- [ ] Frontend service created from same GitHub repo
- [ ] Frontend root directory set to `apps/web`
- [ ] Build command set:
  - [ ] `npm install && npm run build`
- [ ] Start command set:
  - [ ] `npm run start`
- [ ] First deploy succeeded
- [ ] Landing page loads correctly

### Frontend Environment Variables

- [ ] `BACKEND_URL=https://<backend>.up.railway.app`
- [ ] `NEXTAUTH_SECRET` (must match backend)
- [ ] `NEXTAUTH_URL=https://<frontend>.up.railway.app` (later set to custom domain)
- [ ] `GOOGLE_CLIENT_ID`
- [ ] `GOOGLE_CLIENT_SECRET`
- [ ] `NEXT_PUBLIC_APPLE_AUTH_ENABLED=false` (or true when Apple is configured)
- [ ] `APPLE_CLIENT_ID` (optional)
- [ ] `APPLE_CLIENT_SECRET` (optional)

---

## 5) Google OAuth Configuration

- [ ] Google Cloud project created
- [ ] OAuth consent screen configured
- [ ] OAuth Web client created
- [ ] Authorized JavaScript origins added:
  - [ ] `https://parently-ai.com`
  - [ ] `https://<frontend>.up.railway.app`
  - [ ] `http://localhost:3001`
- [ ] Authorized redirect URIs added:
  - [ ] `https://parently-ai.com/api/auth/callback/google`
  - [ ] `https://<frontend>.up.railway.app/api/auth/callback/google`
  - [ ] `http://localhost:3001/api/auth/callback/google`
- [ ] Google login tested in production
- [ ] Account chooser verified (user can pick account each sign-in)
- [ ] Logged-in backend proxy calls include bearer auth
- [ ] New user onboarding redirect works
- [ ] Returning user dashboard redirect works

---

## 6) Stripe Billing Setup (SaaS)

- [ ] Stripe account ready
- [ ] Product created: `Parently Premium`
- [ ] Price created: `$3/month` recurring
- [ ] `STRIPE_PRICE_ID` copied to backend env
- [ ] `STRIPE_SECRET_KEY` set in backend env

### Stripe Webhook

- [ ] Webhook endpoint created:
  - [ ] `https://<backend>.up.railway.app/api/billing/webhook`
- [ ] Webhook events enabled:
  - [ ] `checkout.session.completed`
  - [ ] `customer.subscription.updated`
  - [ ] `customer.subscription.deleted`
- [ ] `STRIPE_WEBHOOK_SECRET` copied to backend env
- [ ] Checkout -> webhook -> entitlement activation tested

### Billing Product Behavior

- [ ] Logged-out user sees sign-in flow
- [ ] Logged-in free user sees upgrade flow
- [ ] Free digest limit returns HTTP `402`
- [ ] Premium unlock verified after payment
- [ ] Premium users bypass paywall

---

## 7) Cron Jobs (Daily Automation)

- [ ] Cron trigger configured for:
  - [ ] `POST /api/internal/run-daily-digests`
- [ ] Cron trigger configured for:
  - [ ] `POST /api/internal/refresh-school-sources`
- [ ] `X-Cron-Secret` header configured with `CRON_SECRET`
- [ ] Daily digest cron endpoint secured and scheduled
- [ ] School source refresh cron endpoint secured and scheduled
- [ ] Cron executions verified in logs

---

## 8) Core Product Path Verification

- [ ] User can sign in
- [ ] User onboarding runs end-to-end
- [ ] Child can be added
- [ ] School discovery starts and returns status
- [ ] Digest can run manually
- [ ] Digest shows in dashboard and history
- [ ] Notifications appear and can be marked read
- [ ] Settings save successfully
- [ ] End-to-end happy path verified:
  - [ ] login -> onboarding -> source discovery -> digest run -> history

---

## 9) Support, Privacy, Terms, Contact

- [ ] `/support` page deployed
- [ ] `/privacy` page deployed
- [ ] `/terms` page deployed
- [ ] Footer links to support/privacy/terms verified
- [ ] Support email shown consistently (`support@parently-ai.com`)
- [ ] Contact form submits successfully
- [ ] SMTP send test completed

---

## 10) Custom Domain + DNS + SSL

- [ ] `parently-ai.com` connected to Railway frontend
- [ ] SSL certificate active
- [ ] `NEXTAUTH_URL` updated to `https://parently-ai.com`
- [ ] `FRONTEND_APP_URL` updated to `https://parently-ai.com`
- [ ] `ALLOWED_ORIGINS` updated with production domain(s)
- [ ] Google OAuth origins/redirects updated for custom domain
- [ ] CORS allows custom domain + Railway domain

---

## 11) PWA Readiness

- [ ] `manifest.json` verified
- [ ] App icons verified (`192x192`, `512x512`)
- [ ] Install prompt works on Android Chrome
- [ ] Standalone launch behavior verified
- [ ] `/.well-known/assetlinks.json` exists
- [ ] `assetlinks.json` updated with release signing cert SHA256 before Play rollout

---

## 12) Google Play Store Deployment (TWA/PWA Wrapper)

- [ ] Google Play Console app created
- [ ] App details completed
- [ ] AAB generated via PWABuilder/Bubblewrap
- [ ] AAB uploaded to internal testing
- [ ] Privacy policy URL added (`https://parently-ai.com/privacy`)
- [ ] Support URL added (`https://parently-ai.com/support`)
- [ ] Contact email added (`support@parently-ai.com`)
- [ ] Screenshots uploaded (phone/tablet as required)
- [ ] Content rating completed
- [ ] Data safety form completed
- [ ] App access/testing instructions added for reviewers
- [ ] Internal test approved and installed successfully
- [ ] Production rollout planned

---

## 13) Launch Readiness (Go/No-Go)

- [ ] Backend logs clean (no auth/stripe/webhook errors)
- [ ] Frontend logs clean (no critical runtime errors)
- [ ] OAuth redirect mismatch issues resolved
- [ ] Stripe webhook delivery success > 99%
- [ ] Alerting/monitoring setup complete (recommended)
- [ ] Backup/rollback plan documented
- [ ] Final smoke test completed on production domain
- [ ] Stripe test payments pass in test mode
- [ ] Stripe live keys and live webhook cutover planned before public launch

---

## Common Pitfalls to Re-check

- [ ] Backend not binding to `0.0.0.0:$PORT`
- [ ] Missing/incorrect OAuth redirect URI
- [ ] Missing Authorization header in backend-proxied requests
- [ ] Stripe webhook secret from wrong mode (test vs live)
- [ ] `ALLOWED_ORIGINS` missing custom domain
- [ ] `NEXTAUTH_SECRET` mismatch between frontend/backend
- [ ] `assetlinks.json` missing or using wrong certificate fingerprint

---

## Post-Launch (Week 1)

- [ ] Track sign-up -> onboarding completion -> first digest conversion
- [ ] Track free -> paid conversion funnel
- [ ] Review support inbox daily
- [ ] Review Stripe failed payment events
- [ ] Capture user feedback and prioritize fixes
