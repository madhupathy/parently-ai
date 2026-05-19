# Parently: Never miss important school news again

![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

---

## The Problem

Your child's school sends emails to five different addresses, posts events on an unmaintained website, shares PDFs through a class app, and texts last-minute reminders at 7 AM. You miss the field-trip permission deadline. Again.

## The Solution

**Parently** pulls every channel together — Gmail, Google Drive, school websites, and public calendars — and turns the noise into a single calm daily digest, grouped by child, delivered at the time you choose.

---

## Features

- ✅ **Gmail integration** — OAuth-powered scan of school-related emails
- ✅ **AI-powered digest generation** — LangGraph + Gemini extracts events, deadlines, and action items
- ✅ **Per-child grouping** — each digest section is scoped to one child
- ✅ **Daily email delivery** — sent to your inbox at your preferred time
- ✅ **Timezone-aware scheduling** — works correctly wherever you are
- ✅ **Priority rules** — mark senders as "always important" or "never notify"
- ✅ **Full-text search in digest history** — find any past announcement instantly
- ✅ **PWA — works offline on mobile** — install to home screen, read cached digests without signal
- ✅ **Free tier available** — 30 lifetime digests, no credit card required

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/your-org/parently.git
cd parently/parently

# 2. Set up the backend (Python 3.11+)
cd apps/backend
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp env.example .env          # fill in required keys (see Environment Variables below)
alembic upgrade head
uvicorn app:app --reload --port 8000

# 3. Set up the frontend (Node 18+) — open a new terminal
cd apps/web
npm install
cp env.example .env.local    # fill in required keys
npm run dev

# 4. Open the app
#   Frontend:        http://localhost:3000
#   Backend API docs: http://localhost:8000/docs

# 5. Run the test suite (optional)
cd apps/backend
python -m pytest tests/ -v
```

Minimum required `.env` keys for local development:

| Key | Where |
|---|---|
| `NEXTAUTH_SECRET` | frontend + backend (must match) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | frontend + backend |
| `GEMINI_API_KEY` | backend |
| `NEXTAUTH_URL` | frontend (`http://localhost:3000` locally) |
| `BACKEND_URL` | frontend (`http://localhost:8000` locally) |

---

## Architecture

```
Browser / PWA (Next.js 14, App Router)
  ├─ NextAuth  →  Google OAuth (+ optional Apple)
  ├─ JWT bearer tokens  →  FastAPI backend
  ├─ Service worker  →  offline app shell cache
  └─ /api/* proxy routes

FastAPI backend (Python 3.11)
  ├─ Auth sync + entitlement enforcement
  ├─ Smart school discovery + source verification
  ├─ Connector ingestion (Gmail, Drive, ICS, RSS, PDF)
  ├─ LangGraph digest pipeline
  │    ├─ Collect + classify content per child
  │    ├─ RAG retrieval over pgvector
  │    ├─ Action / date extraction (Gemini)
  │    └─ Compose per-child digest sections
  ├─ Digest persistence + email delivery (aiosmtplib)
  ├─ Notification fan-out
  └─ Stripe billing + webhooks

Neon Postgres (pgvector)
  ├─ Core entities: users, children, sources, digests
  ├─ Entitlements + billing state
  └─ Vector embeddings (document_chunks + embeddings)
```

### Stack

| Layer | Technology | Role |
|---|---|---|
| Frontend | Next.js 14 (App Router) | PWA, NextAuth, UI |
| Backend | FastAPI (Python 3.11) | REST API, cron jobs |
| AI pipeline | LangGraph + Gemini (OpenAI fallback) | Digest generation |
| Database | PostgreSQL + pgvector (Neon) | Data + vector search |
| Auth | NextAuth + JWT (shared secret) | Session management |
| Billing | Stripe Checkout + Webhooks | Subscriptions |
| Email | aiosmtplib + Jinja2 | Digest delivery |
| Hosting | Railway | Frontend + backend |

---

## Environment Variables

### Backend (`apps/backend/env.example`)

| Variable | Required | Description |
|----------|----------|-------------|
| `BACKEND_DATABASE_URL` | Yes | `sqlite:///./parently.db` (dev) or Neon Postgres URI (prod) |
| `NEXTAUTH_SECRET` | Yes | Must exactly match the frontend value — generate with `openssl rand -hex 32` |
| `GEMINI_API_KEY` | Yes | Primary LLM — [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth for Gmail token refresh |
| `STRIPE_SECRET_KEY` | Yes | Stripe billing |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing |
| `STRIPE_PRICE_ID` | Yes | $3/month recurring price ID |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Yes | Outbound email for digest delivery |
| `CRON_SECRET` | Yes | Header secret for internal cron endpoints |
| `OPENAI_API_KEY` | Optional | Fallback LLM |

### Frontend (`apps/web/env.example`)

| Variable | Required | Description |
|----------|----------|-------------|
| `BACKEND_URL` | Yes | Backend base URL — server-side only |
| `NEXTAUTH_SECRET` | Yes | Must match backend exactly |
| `NEXTAUTH_URL` | Yes | Public frontend URL |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth |
| `AUTH_TRUST_HOST` | Yes | Set `true` on Railway |

---

| Variable | Required | Notes |
|---|---|---|
| `BACKEND_DATABASE_URL` | Yes | Neon Postgres connection string in production |
| `NEXTAUTH_SECRET` | Yes | Must exactly match frontend `NEXTAUTH_SECRET` |
| `FRONTEND_APP_URL` | Yes | `https://parently-ai.com` |
| `ALLOWED_ORIGINS` | Yes | Include production frontend domain and any active Railway frontend domain |
| `CRON_SECRET` | Yes | Secret for internal scheduled endpoints |
| `SUPPORT_EMAIL` | Yes | Support sender address |
| `GEMINI_API_KEY` | Yes | Primary model provider key |
| `GEMINI_MODEL` | Yes | Example: `gemini-flash-latest` |
| `GEMINI_EMBEDDING_MODEL` | Yes | Recommended: `gemini-embedding-001` |
| `RAG_EMBEDDING_DIMENSION` | Yes | Must match stored/query vectors, default `1536` |
| `OPENAI_API_KEY` | Optional | Fallback model provider key |
| `OPENAI_MODEL` | Optional | Example: `gpt-4o-mini` |
| `GOOGLE_CLIENT_ID` | Yes | Required for Gmail token refresh |
| `GOOGLE_CLIENT_SECRET` | Yes | Required for Gmail token refresh |
| `STRIPE_SECRET_KEY` | Yes | Stripe secret key, mode-specific |
| `STRIPE_PRICE_ID` | Yes | Stripe recurring price ID, same mode as key/secret |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret |
| `SMTP_HOST` | Yes | Outbound mail server host |
| `SMTP_PORT` | Yes | Outbound mail server port |
| `SMTP_USER` | Yes | SMTP username |
| `SMTP_PASSWORD` | Yes | SMTP password |
| `SMTP_FROM` | Yes | Envelope/from email |
| `SMTP_FROM_NAME` | Yes | Sender display name |
| `SMTP_SECURE` | Yes | `true` or `false` depending on provider settings |

---

## Deployment (Railway)

1. Create two Railway services: one for the frontend (`apps/web`), one for the backend (`apps/backend`).
2. Set root directory to `parently/apps/web` and `parently/apps/backend` respectively, or use the provided `railway.json` in each app directory.
3. Add all required environment variables to each service (see table above).
4. For the database, provision a Neon Postgres instance and set `BACKEND_DATABASE_URL`.
5. Run migrations on first deploy: `alembic upgrade head` (Railway can run this as a release command).
6. Set `AUTH_TRUST_HOST=true` on the frontend service.
7. Add your Railway frontend domain to `ALLOWED_ORIGINS` on the backend service.
8. Configure Google OAuth: add both `https://parently-ai.com` and your Railway frontend URL to the allowed redirect URIs in Google Cloud Console.

For a step-by-step operational checklist see `deployment.md`.

---

## Plans and Pricing

| Plan | Price | Digest limit | History |
|---|---|---|---|
| Free | $0 | 30 lifetime digests | 7 days |
| Premium | $3/month | Unlimited | 365 days |

When free limits are exhausted, the backend returns HTTP 402 and the frontend prompts upgrade.

---

## Repository Layout

```
parently/
  apps/
    backend/
      app.py              # FastAPI entry point
      config.py
      dependencies.py
      routers/            # auth, children, digest, notifications, preferences, …
      services/           # ingestion, email, billing, discovery, …
      storage/            # SQLAlchemy models + Alembic migrations
      agents/             # LangGraph digest pipeline
      tests/
      prompts/
    web/
      app/                # Next.js App Router pages
        api/              # Proxy routes → backend
        dashboard/
        digest/
        settings/
          schedule/       # Digest scheduling UI
        notifications/
      components/
        header.tsx
        notification-center.tsx
        daily-digest.tsx
        …
      lib/
      public/
        manifest.json     # PWA manifest
        sw.js             # Service worker (offline support)
```

---

## Contributing

1. Fork the repo and create a feature branch from `main`.
2. Follow the existing code style — TypeScript strict mode on the frontend, type-annotated Python on the backend.
3. Add or update tests for any logic changes (`apps/backend/tests/`).
4. Ensure migrations are additive (no column drops without a data-preservation plan).
5. Open a pull request with a clear description of the problem and solution.
6. All CI checks (lint, type-check, migration safety, tests) must pass before merge.

Bug reports and feature requests are welcome via GitHub Issues. For security disclosures, email support@parently-ai.com directly.
