<div align="center">

# Parently AI

**One calm summary. Everything your child's school sent this week.**

Parently AI connects to your Gmail, Google Drive, school websites, and class apps (ClassDojo, Brightwheel, Skyward), and delivers a single clear daily digest — grouped per child, with events, deadlines, and action items extracted so you don't have to.

[![Migrations](https://github.com/madhupathy/parently-ai/actions/workflows/migrations.yml/badge.svg)](https://github.com/madhupathy/parently-ai/actions/workflows/migrations.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)

</div>

---

## The Problem

School communication is fragmented across too many channels:
- An **email** from the teacher about Thursday's field trip
- A **ClassDojo message** about a permission slip due Friday
- A **school website update** listing the spring calendar
- A **Google Drive PDF** with the updated lunch menu
- A **Brightwheel notification** about the fundraiser deadline

Parents miss things. Kids show up without the right supplies. Permission slips come home unsigned. The information was sent — it just got buried in four different apps.

Parently AI reads all of it and tells you what matters, in plain language, every morning.

---

## How It Works

```
Your Gmail        ClassDojo / Brightwheel    School website    Google Drive
     │                    │                        │                │
     └────────────────────┴────────────────────────┴────────────────┘
                                    │
                          Smart school discovery
                          (auto-finds calendars,
                           feeds, and doc pages)
                                    │
                          LangGraph digest pipeline
                          ┌─────────────────────────┐
                          │ fetch → classify         │
                          │ → extract actions/dates  │
                          │ → group per child        │
                          │ → compose digest         │
                          └─────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
              Daily email                    In-app dashboard
                                          (PWA — works on mobile)
```

**For each child**, the digest shows:
- **Today** — anything happening today or requiring immediate attention
- **Upcoming** — events in the next 7 days
- **Actions** — things you need to do (sign forms, pay fees, bring items)
- **FYI** — announcements, policy updates, newsletter highlights

---

## Quick Start

### Prerequisites
- Python 3.11+, Node.js 18+
- A Google account with Gmail access
- SQLite (local dev) or Neon Postgres + pgvector (production)

### Backend

```bash
cd apps/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env          # fill in NEXTAUTH_SECRET, GEMINI_API_KEY
alembic upgrade head
uvicorn app:app --reload --port 8000
```

### Frontend

```bash
cd apps/web
npm install
cp env.example .env.local    # fill in NEXTAUTH_SECRET, GOOGLE_CLIENT_ID/SECRET
npm run dev
# → http://localhost:3000
```

### Run the test suite

```bash
cd apps/backend && python -m pytest tests/ -v
```

---

## Key Features

### Smart School Discovery
Type your child's school name. Parently finds the official website, calendar feeds (ICS, RSS, HTML), and downloadable PDFs automatically — no manual URL entry.

```
"Harmony Science Academy Georgetown TX"
    → Found: school website, academic calendar ICS, parent newsletter feed
    → Discovered 3 sources — confirm to start ingesting
```

### Platform Detection
Parently recognizes email patterns from ClassDojo, Brightwheel, Kumon, and Skyward — and extracts structured data without needing direct API access to those platforms.

### Per-Child Digest
Every piece of content is mapped to the right child. If you have two kids at different schools, their digests are completely separate. No cross-contamination.

### Gmail OAuth — No Password Required
Connect Gmail with a standard Google OAuth flow. Parently requests `gmail.readonly` scope only. Your credentials are never stored in plain text.

---

## Environment Variables

> **Never commit `.env` or `.env.local`** — they are gitignored. Use `env.example` as a template only.

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

## Plans

| Plan | Price | Digests | History | Features |
|------|-------|---------|---------|---------|
| Free | $0 | 30 lifetime | 7 days | Gmail + school discovery |
| Premium | $3/month | Unlimited | 365 days | + Drive, priority processing |

When free limits are exhausted, the backend returns HTTP `402` and the frontend shows the upgrade modal.

---

## Database Migrations

Every schema change ships as an Alembic migration:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head

# Before any deployment — verify the chain from scratch
alembic downgrade base && alembic upgrade head
```

---

## Architecture

```
apps/web/                         Next.js 14 + NextAuth + Tailwind
  app/api/*/                      API proxy routes → FastAPI backend
  components/                     Dashboard, digest, onboarding UI

apps/backend/
  app.py                          FastAPI entrypoint
  agents/graph.py                 LangGraph digest pipeline
  services/
    connectors/                   Gmail, Drive, ClassDojo, Brightwheel connectors
    school_discovery.py           LLM-powered source discovery
    email_classifier.py           Email → school/child/category mapping
    llm.py                        Gemini + OpenAI service layer
  routers/                        Auth, digest, sources, billing, notifications
  storage/models.py               SQLAlchemy models (users, children, sources, digests)
  alembic/versions/               Migration chain
```

---

## Production Notes

- **Domain**: `https://parently-ai.com`
- **Hosting**: Railway (frontend + backend), Neon Postgres
- `NEXTAUTH_SECRET` must be **identical** in frontend and backend — a mismatch causes silent auth failures
- `AUTH_TRUST_HOST=true` is **required** on Railway's frontend service
- All Stripe variables must come from the **same mode** (test or live)
- `ALLOWED_ORIGINS` must include the exact production frontend domain

Full production checklist in [deployment.md](deployment.md).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Run `pytest tests/ -v` before submitting. Include an Alembic migration for any schema change. Never commit credentials.

## License

All rights reserved.
