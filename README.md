# Parently AI

> **Calm, actionable daily school digests** — consolidating school communications from Gmail, Google Drive, school websites, and calendars into a single per-child summary.

[![Migrations](https://github.com/madhupathy/parently-ai/actions/workflows/migrations.yml/badge.svg)](https://github.com/madhupathy/parently-ai/actions/workflows/migrations.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-Proprietary-lightgrey)](#license)

Parents receive fragmented messages across email, school apps, calendars, and websites. Parently AI ingests all of it and delivers one clear, context-specific digest per child — with events, deadlines, and action items extracted automatically.

---

## Screenshots

> Add screenshots to `docs/screenshots/` and update the paths below.
>
> **Dashboard** — daily digest with grouped events and action items  
> ![Parently AI Dashboard](docs/screenshots/dashboard.png)
>
> **Onboarding** — school discovery and source setup  
> ![Parently AI Onboarding](docs/screenshots/onboarding.png)

---

## Features

- Smart school source discovery from name + location
- Gmail and Google Drive OAuth connectors
- Automatic platform detection (ClassDojo, Brightwheel, Kumon, Skyward)
- Calendar ingestion: ICS, RSS/Atom, HTML, and PDF sources
- Per-child grouped daily digest via LangGraph workflow
- Notification center with unread counts
- Subscription billing via Stripe (Free / Premium $3/month)
- Mobile-friendly PWA

---

## Architecture

```
Next.js frontend (apps/web)
  → NextAuth (Google + optional Apple)
  → internal API proxy routes (/api/*)
  → FastAPI backend (apps/backend)
       → LangGraph digest workflow
       → discovery + ingestion services
       → Postgres + pgvector (Neon)
       → Stripe billing + webhooks
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- SQLite (default for local) or Postgres + pgvector (production)

### Backend

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp env.example .env               # fill in your values
alembic upgrade head
uvicorn app:app --reload --port 8000
```

### Frontend

```bash
cd apps/web
npm install
cp env.example .env.local         # fill in your values
npm run dev
# → http://localhost:3000
```

### Tests

```bash
cd apps/backend
python -m pytest tests/ -v
```

---

## Environment Variables

> ⚠️ **Never commit `.env` or `env.local` files.** They are gitignored. Use the `env.example` files as templates.

### Backend (`apps/backend/env.example`)

| Variable | Required | Description |
|---|---|---|
| `BACKEND_DATABASE_URL` | Yes | SQLite URI for local; Neon Postgres URI for production |
| `NEXTAUTH_SECRET` | Yes | Must match frontend `NEXTAUTH_SECRET` |
| `FRONTEND_APP_URL` | Yes | `https://parently-ai.com` in production |
| `ALLOWED_ORIGINS` | Yes | Comma-separated allowed frontend origins |
| `CRON_SECRET` | Yes | Secret header for internal cron endpoints |
| `GEMINI_API_KEY` | Yes | Primary LLM provider key |
| `GEMINI_MODEL` | Yes | e.g. `gemini-flash-latest` |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret |
| `STRIPE_SECRET_KEY` | Yes | Stripe secret key (test or live) |
| `STRIPE_PRICE_ID` | Yes | Stripe recurring price ID |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret |
| `SMTP_HOST` | Yes | Outbound mail server |
| `SMTP_USER` | Yes | SMTP username |
| `SMTP_PASSWORD` | Yes | SMTP password |
| `OPENAI_API_KEY` | Optional | Fallback LLM key |

### Frontend (`apps/web/env.example`)

| Variable | Required | Description |
|---|---|---|
| `BACKEND_URL` | Yes | Backend base URL (server-side only) |
| `NEXTAUTH_URL` | Yes | Public frontend URL |
| `NEXTAUTH_SECRET` | Yes | Must match backend `NEXTAUTH_SECRET` |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret |
| `AUTH_TRUST_HOST` | Yes | Set `true` on Railway |

---

## Database Migrations

Schema changes must ship as Alembic migrations:

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

Verify the chain runs from scratch before deploying:

```bash
alembic downgrade base
alembic upgrade head
```

---

## Key API Endpoints

| Area | Method | Path |
|---|---|---|
| Health | `GET` | `/healthz` |
| Auth sync | `POST` | `/api/auth/sync` |
| School discovery | `POST` | `/api/sources/discover` |
| Setup status | `GET` | `/api/setup/status` |
| Daily digest | `POST` | `/api/internal/run-daily-digests` |
| Billing checkout | `POST` | `/api/billing/create-checkout-session` |
| Notifications | `GET` | `/api/notifications` |

---

## Plans

| Plan | Price | Digest Limit | History |
|---|---|---|---|
| Free | $0 | 30 lifetime | 7 days |
| Premium | $3/month | Unlimited | 365 days |

Free-plan limits are enforced server-side; the backend returns HTTP `402` when limits are reached.

---

## Deployment

See [deployment.md](deployment.md) for the full production checklist covering Railway, Neon Postgres, Stripe, Google OAuth, cron jobs, and DNS/SSL setup.

**Common pitfalls:**
- `NEXTAUTH_SECRET` must be identical in frontend and backend
- `AUTH_TRUST_HOST=true` is required on Railway
- `ALLOWED_ORIGINS` must include the exact production frontend domain
- Stripe key, price ID, and webhook secret must all come from the same mode (test or live)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). In short:

1. Fork → branch → commit → PR
2. Run `pytest tests/ -v` before pushing
3. Include an Alembic migration for any schema change
4. Never commit `.env` files or credentials

---

## License

All rights reserved. Contact the maintainers for licensing inquiries.
