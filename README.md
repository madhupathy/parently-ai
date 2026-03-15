# Parently AI

Parently AI gives parents a calm, actionable daily school digest instead of fragmented messages across email, school websites, and calendars. The platform combines smart source discovery, targeted ingestion, and AI summarization in a production SaaS architecture.

## Product Overview

Parently AI:
- consolidates school communication from Gmail, Google Drive, school websites, and public calendars;
- groups outputs per child, so each digest is context-specific;
- extracts events, deadlines, announcements, and action items;
- provides a mobile-friendly PWA experience with subscription billing.

## Current Deployment Status

- Production frontend domain: `https://parently-ai.com`
- Backend public URL: `https://<backend>.up.railway.app` (placeholder until finalized)
- Frontend Railway URL: `https://<frontend>.up.railway.app` (placeholder until finalized)
- Hosting: Railway (frontend + backend), Neon Postgres (`pgvector`)
- Billing mode: set in Stripe (`test` or `live`)
- Support email: `support@parently-ai.com`

## Architecture

### High-level system

```
Next.js frontend (apps/web)
  -> NextAuth session + JWT minting
  -> internal API proxy routes (/api/*)
  -> FastAPI backend (apps/backend)
       -> LangGraph digest workflow
       -> discovery + ingestion services
       -> Postgres + pgvector (Neon)
       -> Stripe billing + webhooks
```

### Core backend domains
- Auth/session sync and entitlement checks
- Smart school discovery and source verification
- Connector ingestion (Gmail, Drive, public sources)
- Digest composition and notification fan-out
- Billing and subscription state transitions

## Key Features

- Smart school discovery from name + location (website/calendar auto-discovery)
- Per-child grouped daily digest output
- Automatic email-platform detection (ClassDojo, Brightwheel, Kumon, Skyward)
- Calendar ingestion across ICS, RSS/Atom, HTML, and PDF sources
- Notification center with unread counts and digest-linked updates
- Usage and entitlement enforcement with premium upgrade flow

## Plans and Pricing

| Plan | Price | Digest limits | History | Access |
|---|---|---|---|---|
| Free | $0 | 30 lifetime digests | 7 days | Core ingestion + discovery |
| Premium | $3/month | Unlimited | 365 days | Priority usage + full history |

When free limits are exhausted, backend entitlement checks return HTTP `402` and frontend prompts upgrade.

## Repository Layout

```
apps/
  backend/
    app.py
    config.py
    dependencies.py
    routers/
    services/
    storage/
    agents/
    tests/
    prompts/
    alembic/
  web/
    app/
    components/
    lib/
    auth.ts
    middleware.ts
```

## Local Development

### Backend

```bash
cd apps/backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy env.example .env
alembic upgrade head
uvicorn app:app --reload --port 8000
```

### Frontend

```bash
cd apps/web
npm install
copy env.example .env.local
npm run dev
```

### Test suite

```bash
cd apps/backend
python -m pytest tests/ -v
```

## Environment Variables

Use exactly these variables in production.

### Frontend (`apps/web`)

| Variable | Required | Notes |
|---|---|---|
| `BACKEND_URL` | Yes | Backend base URL used by frontend server routes |
| `NEXTAUTH_SECRET` | Yes | Must exactly match backend `NEXTAUTH_SECRET` |
| `NEXTAUTH_URL` | Yes | Public frontend URL; use `https://parently-ai.com` in production |
| `AUTH_TRUST_HOST` | Yes | Set `true` on Railway |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth web client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth web client secret |
| `NEXT_PUBLIC_APPLE_AUTH_ENABLED` | Yes | `true` or `false` feature flag |
| `APPLE_CLIENT_ID` | Conditional | Required when Apple auth is enabled |
| `APPLE_CLIENT_SECRET` | Conditional | Required when Apple auth is enabled |

### Backend (`apps/backend`)

| Variable | Required | Notes |
|---|---|---|
| `BACKEND_DATABASE_URL` | Yes | Neon Postgres connection string in production |
| `NEXTAUTH_SECRET` | Yes | Must exactly match frontend `NEXTAUTH_SECRET` |
| `FRONTEND_APP_URL` | Yes | `https://parently-ai.com` |
| `ALLOWED_ORIGINS` | Yes | Include production frontend domain and any active Railway frontend domain |
| `CRON_SECRET` | Yes | Secret for internal scheduled endpoints |
| `SUPPORT_EMAIL` | Yes | Support sender address |
| `GEMINI_API_KEY` | Yes | Primary model provider key |
| `GEMINI_MODEL` | Yes | Example: `gemini-1.5-flash` |
| `OPENAI_API_KEY` | Optional | Fallback model provider key |
| `OPENAI_MODEL` | Optional | Example: `gpt-4o-mini` |
| `STRIPE_SECRET_KEY` | Yes | Stripe secret key, mode-specific |
| `STRIPE_PRICE_ID` | Yes | Stripe recurring price ID, same mode as key/secret |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret, same mode as key/price |
| `SMTP_HOST` | Yes | Outbound mail server host |
| `SMTP_PORT` | Yes | Outbound mail server port |
| `SMTP_USER` | Yes | SMTP username |
| `SMTP_PASSWORD` | Yes | SMTP password |
| `SMTP_FROM` | Yes | Envelope/from email |
| `SMTP_FROM_NAME` | Yes | Sender display name |
| `SMTP_SECURE` | Yes | `true` or `false` depending on provider settings |

## Authentication

- Frontend uses NextAuth (Google + optional Apple providers).
- Backend verifies JWT bearer tokens using the shared `NEXTAUTH_SECRET`.
- Frontend proxy routes call backend APIs with `Authorization: Bearer <token>`.
- New users are synced to backend and routed to onboarding before dashboard access.

## Smart School Discovery

Discovery runs during onboarding or when a child school profile is updated:
1. Query generation from school name/location.
2. LLM candidate source discovery.
3. Site crawl for official pages and feed links.
4. Deterministic/LLM verification scoring.
5. Source persistence and integration mapping by child.

Daily refresh jobs keep school sources current and re-ingest updated content.

## Connectors and Sources

### Official/API-backed connectors
- Gmail (OAuth)
- Google Drive (OAuth)

### Smart parsing sources (no direct third-party API dependency)
- ClassDojo email patterns
- Brightwheel email patterns
- Kumon email patterns
- Skyward email patterns

### Public source ingestion
- School websites
- Calendar sources (ICS, RSS/Atom, HTML calendar pages, PDF calendars)

## Digest Pipeline

Digest generation uses a staged LangGraph flow:
- collect connector and school-source context;
- classify and map content by child;
- run retrieval over vector context where applicable;
- extract actions and dates;
- compose a per-child daily digest;
- persist digest, sections, usage, and notification artifacts.

## Notifications

- Unread-count notification bell in frontend header.
- Digest-related and system notification types.
- Read and mark-all-read APIs for notification state management.

## Billing

- Stripe checkout creates/updates subscriptions for Premium.
- Webhook events reconcile entitlement state.
- Free-to-premium boundary enforcement occurs in backend dependencies.
- Plan limits are enforced server-side before digest generation.

## Database

- Development default: lightweight local setup for rapid iteration.
- Production: Neon Postgres with `pgvector`.
- Schema management via Alembic migrations.
- Core entities include users, children, sources, digests, entitlements, billing, and notifications.

## Important API Endpoints

| Area | Method | Path |
|---|---|---|
| Health | `GET` | `/healthz` |
| Auth sync | `POST` | `/api/auth/sync` |
| Discovery start | `POST` | `/api/sources/discover` |
| Discovery status | `GET` | `/api/sources/discover/{job_id}` |
| Child sources | `GET` | `/api/sources/{child_id}` |
| Confirm source | `POST` | `/api/sources/{source_id}/confirm` |
| Remove source | `DELETE` | `/api/sources/{source_id}` |
| Billing checkout | `POST` | `/api/billing/create-checkout-session` |
| Billing webhook | `POST` | `/api/billing/webhook` |
| Daily digest cron | `POST` | `/api/internal/run-daily-digests` |
| Refresh sources cron | `POST` | `/api/internal/refresh-school-sources` |

## Production Notes and Common Pitfalls

- `NEXTAUTH_SECRET` must match in frontend and backend.
- `NEXTAUTH_URL` must not be blank in production.
- `AUTH_TRUST_HOST=true` is required on Railway.
- `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, and `STRIPE_WEBHOOK_SECRET` must come from the same Stripe mode (`test` or `live`).
- `ALLOWED_ORIGINS` must include the actual frontend domain (`https://parently-ai.com`) and any active Railway frontend domain.
- Backend must bind to `0.0.0.0:$PORT`.
- Google OAuth allowed origins and redirect URIs must include production and Railway frontend domains.
- Keep `FRONTEND_APP_URL` aligned with the active production frontend URL.

For operational deployment steps, use `deployment.md` (checklist-only).
