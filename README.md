# Parently

**Your parent's desk in your pocket.** Parently is a SaaS that consolidates school communications from Gmail, Google Drive, Skyward, ClassDojo, and Brightwheel into a calm daily digest powered by Gemini 1.5 Flash. It **automatically discovers** your child's school website and calendar from just a name and school — no third-party API integrations needed. FastAPI + LangGraph backend, Next.js 14 + shadcn/ui frontend, installable as a mobile PWA. Deployed on Railway with Neon Postgres + pgvector and Stripe billing.

## Current Deployment Status

- Frontend domain: `https://parently-ai.com` (target production domain)
- Backend domain: `_fill_after_first_Railway_deploy_`
- Stripe mode: `_test_or_live_`
- Support email: `support@parently-ai.com`
- Last verified: `_date_and_owner_`

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Next.js 14 Frontend (PWA)               Railway Service     │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────────┐        │
│  │  Login   │ │Dashboard │ │Pricing │ │  Settings  │        │
│  └──────────┘ └──────────┘ └────────┘ └────────────┘        │
│  ┌────────────────────────────────────────────────────┐      │
│  │  Onboarding: Name+School → Discover → Connect → Go│      │
│  └────────────────────────────────────────────────────┘      │
│           │  API Proxy Routes (/api/*)  │                    │
│           │  JWT (HS256, jose)          │                    │
└───────────┼─────────────────────────────┼────────────────────┘
            │  Authorization: Bearer JWT  │
┌───────────▼─────────────────────────────▼────────────────────┐
│  FastAPI Backend                         Railway Service      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  LangGraph Digest Pipeline (9 nodes)                   │  │
│  │  gmail → connectors → school_sources → classify_emails │  │
│  │  → pdfs → rag → extract → compose (per-child grouped) │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Smart School Discovery Pipeline                       │  │
│  │  query_builder → LLM candidates → site_fetcher →      │  │
│  │  source_verifier → calendar/website ingestion          │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌──────────┐ ┌────────────┐ ┌────────────────────┐         │
│  │ Billing  │ │ Entitle-   │ │ LLM Usage Tracking │         │
│  │ (Stripe) │ │ ments      │ │ (tokens + cost)    │         │
│  └──────────┘ └────────────┘ └────────────────────┘         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Sources: Gmail │ Drive │ School Website │ ICS/RSS/PDF │  │
│  │  Email Parsing: ClassDojo │ Brightwheel │ Kumon │ Skyward│ │
│  └────────────────────────────────────────────────────────┘  │
│  Neon Postgres + pgvector │ Alembic Migrations               │
└──────────────────────────────────────────────────────────────┘
```

## Key Features

- **Smart School Discovery** — Type a school name and city; Parently uses LLM + web crawling to find the school website, calendar page, ICS feeds, RSS feeds, and PDF calendars automatically
- **Per-Child Digests** — Each child gets their own section in the daily digest with events, announcements, and action items specific to their school
- **Email Platform Detection** — Automatically recognizes and tags emails from ClassDojo, Brightwheel, Kumon, and Skyward by sender domain — no API keys needed
- **Calendar Ingestion** — Parses ICS, RSS/Atom, HTML calendar pages, and PDF calendars into structured events stored in the RAG vector store
- **Versioned Prompt System** — All LLM prompts stored as markdown files with variable substitution from a shared context JSON
- **Notification System** — Slack-like bell dropdown with unread badges, per-digest notifications, mark-all-read
- **Digest Idempotency** — One digest per day per user, upserted by date

## Plans & Pricing

| Feature | Free | Premium ($3/mo) |
|---|---|---|
| Digests | 30 lifetime | Unlimited |
| School discovery | Unlimited | Unlimited |
| Connectors + smart parsing | All | All |
| AI summarization | Gemini 1.5 Flash | Gemini 1.5 Flash (priority) |
| Digest history | 7 days | 365 days |
| RAG context | pgvector | pgvector |
| Support | Community | Priority |

Free plan users receive HTTP **402** when digests are exhausted, triggering an upgrade modal.

## Repository layout

```
apps/
  backend/                          # FastAPI + LangGraph digest engine
    app.py                          # Entrypoint (routes + cron endpoints)
    config.py                       # Settings from env vars
    dependencies.py                 # JWT auth + entitlement enforcement
    prompts/                        # Versioned LLM prompt files
      common_context.json           # Shared config (keywords, domains, crawl settings)
      school_discovery_prompt_v1.md # LLM school identification
      source_verifier_prompt_v1.md  # LLM source verification
      calendar_extract_prompt_v1.md # LLM calendar event extraction
      website_extract_prompt_v1.md  # LLM website content extraction
      email_school_classifier_prompt_v1.md  # LLM email classification
      digest_compose_prompt_v1.md   # Per-child grouped digest composition
      school_docs_extract_prompt_v1.md      # LLM document extraction
    routers/
      auth.py                       # User sync + session info + onboarding
      digest.py                     # Dashboard, run/refresh, history, get-by-id
      billing.py                    # Stripe checkout + webhook + status
      children.py                   # Children CRUD
      preferences.py                # User preferences CRUD
      search_profiles.py            # Per-child email filter profiles
      uploads.py                    # PDF upload
      integrations.py               # Connector config/status/disconnect
      notifications.py              # List, read, mark-all-read
      sources.py                    # School discovery + source management
    services/
      prompt_loader.py              # Load prompts with variable substitution
      gemini.py                     # Gemini 1.5 Flash + OpenAI fallback
      llm.py                        # Digest summarization (returns usage)
      gmail.py                      # Gmail API + targeted per-child fetch
      gmail_query_builder.py        # Builds Gmail queries from search profiles
      targeted_sync.py              # Per-child incremental Gmail sync
      school_discovery.py           # Tokenize, expand abbreviations, build queries
      school_discovery_llm.py       # LLM candidate school URL generation
      site_fetcher.py               # Crawl domains, find ICS/RSS/PDF links
      source_verifier.py            # Deterministic scoring + LLM gray-zone
      calendar_ingest.py            # ICS/RSS/HTML/PDF → Documents + embeddings
      website_ingest.py             # Crawl school pages → Documents
      school_docs_extract.py        # PDF → facts/actions/dates via LLM
      drive_ingest.py               # Google Drive folder ingestion
      email_classifier.py           # Platform detection + child matching
      pdf.py                        # PDF text extraction (pypdf)
      connectors/                   # Platform adapters (BaseConnector ABC)
    agents/
      graph.py                      # LangGraph digest workflow (9 nodes)
    storage/
      models.py                     # All SQLAlchemy models
      database.py                   # SQLAlchemy engine (Postgres pool)
      rag_store.py                  # pgvector similarity search
    tests/
      test_school_discovery.py      # 37 tests for discovery pipeline
      test_children.py              # Child + model tests
      test_query_builder.py         # Gmail query builder tests
      test_notifications.py         # Notification model tests
      test_rag_store.py             # RAG store tests
    alembic/                        # Database migrations
  web/                              # Next.js 14 + shadcn/ui frontend
    app/
      page.tsx                      # Login (Google/Apple OAuth)
      dashboard/                    # Daily digest + stats + integrations
      pricing/                      # Plans comparison + FAQ
      settings/                     # Profile, children, integrations, billing
      onboarding/                   # 4-step wizard: Welcome → Kids → Sources → Done
      api/                          # JWT-authenticated proxy routes to backend
        sources/                    # Proxy routes for school discovery API
    components/
      integration-cards.tsx         # 3-group layout (Official/Smart/Public)
      daily-digest.tsx              # Today's digest + past 7 days timeline
      header.tsx                    # Nav + bell notification dropdown
      upgrade-modal.tsx             # Stripe upgrade dialog (on 402)
    lib/api.ts                      # Server-side JWT minting + backendFetch
    auth.ts                         # NextAuth.js v5 config
    middleware.ts                   # Route protection
```

## Local development

### Backend

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env  # edit with your keys

alembic upgrade head
uvicorn app:app --reload --port 8000
```

Key backend env vars (see `apps/backend/env.example`):

| Variable | Required | Description |
|---|---|---|
| `BACKEND_DATABASE_URL` | Yes | SQLite (dev) or Neon Postgres URL |
| `NEXTAUTH_SECRET` | Yes | Must match frontend — signs JWTs |
| `GEMINI_API_KEY` | No | Gemini 1.5 Flash (primary LLM) |
| `OPENAI_API_KEY` | No | GPT-4o-mini (fallback LLM) |
| `STRIPE_SECRET_KEY` | No | Stripe API key for billing |
| `STRIPE_WEBHOOK_SECRET` | No | Stripe webhook signature verification |
| `STRIPE_PRICE_ID` | No | $3/month recurring price ID |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins |
| `CRON_SECRET` | No | Railway cron authentication |

### Frontend

```bash
cd apps/web
npm install
cp env.example .env.local  # edit with your keys
npm run dev
```

Key frontend env vars (see `apps/web/env.example`):

| Variable | Required | Description |
|---|---|---|
| `BACKEND_URL` | Yes | Backend URL (server-side only) |
| `NEXTAUTH_SECRET` | Yes | Must match backend |
| `NEXTAUTH_URL` | Yes | Frontend public URL |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret |

### Running tests

```bash
cd apps/backend
python -m pytest tests/ -v   # 101 tests
```

## Authentication

- **Frontend**: NextAuth.js v5 with Google + Apple OAuth
- **Backend**: JWT verification (HS256) using shared `NEXTAUTH_SECRET`
- **Flow**: Frontend mints short-lived HS256 JWTs via `jose` → sends in `Authorization: Bearer` header → backend decodes with PyJWT

The middleware protects `/dashboard`, `/settings`, `/onboarding`, and `/pricing` routes. On login, the frontend syncs the user to the backend via `POST /api/auth/sync`. New users are redirected to `/onboarding` to add children and set preferences.

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new OAuth 2.0 Client ID (Web application)
3. **Authorized JavaScript origins**: `https://parently-ai.com` and `https://<your-frontend>.up.railway.app` (and `http://localhost:3001` for dev)
4. **Authorized redirect URIs**: `https://parently-ai.com/api/auth/callback/google` and `https://<your-frontend>.up.railway.app/api/auth/callback/google` (and `http://localhost:3001/api/auth/callback/google` for dev)
5. Copy the Client ID and Client Secret into your `.env.local`:
   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-your-secret
   ```
6. On Railway, add these same values to the frontend service's environment variables.

> **401 invalid_client error?** This means the `GOOGLE_CLIENT_ID` is a placeholder. You must create real OAuth credentials in Google Cloud Console.

## Smart School Discovery

The discovery pipeline runs when a parent enters their child's school name during onboarding (or later from settings). No official school APIs are used — everything is discovered from the public web.

### Pipeline

1. **Query Builder** (`school_discovery.py`) — Tokenizes the school name, expands abbreviations (e.g. "Harmony" → "Harmony Science Academy", "HSA"), extracts city/state/zip, builds 3–6 search queries
2. **LLM Discovery** (`school_discovery_llm.py`) — Sends queries to Gemini, returns up to 3 candidate school URLs with name, homepage, calendar page, and district site
3. **Site Fetcher** (`site_fetcher.py`) — Crawls each candidate domain (polite 800ms delay, max 5 pages), extracts page snippets, discovers ICS/RSS/PDF links and calendar pages
4. **Source Verifier** (`source_verifier.py`) — Deterministic scoring (0–1) based on name match, calendar presence, ICS/RSS/PDF feeds, domain pattern (.k12./.edu/.org). Scores ≥ 0.82 = auto-verified, 0.40–0.82 = needs_confirmation, < 0.40 = failed. Optional LLM verification for gray zone.
5. **Persist** — Verified sources stored as `SchoolSource` rows, auto-creates `UserIntegration` entries for public_calendar and public_website

### Ingestion (daily cron)

Verified school sources are re-ingested daily via `POST /api/internal/refresh-school-sources`:

- **ICS feeds** → parsed with `icalendar` library → events with categories (holiday, testing, parent_event, etc.)
- **RSS/Atom feeds** → parsed with `feedparser` → announcements with dates
- **HTML calendar pages** → stripped of boilerplate, LLM extracts structured events
- **PDF calendars** → text extracted with `pypdf`, stored as Documents
- **School website** → crawled, boilerplate stripped, LLM extracts announcements

All content is stored as Documents in the RAG vector store with `metadata_json` linking to child_id.

## Connectors & Sources

### Official Integrations (OAuth/API)

| Platform | Method | What it fetches |
|---|---|---|
| **Gmail** | Google API (OAuth token) | School emails, newsletters |
| **Google Drive** | Drive API v3 | Docs, PDFs from a shared folder |
| **ChatGPT** | User-provided API key | AI-powered digest with custom model |

### Smart Parsing (email-based, no API needed)

| Platform | Detection | What it extracts |
|---|---|---|
| **ClassDojo** | `@classdojo.com` sender domain | Points, classroom updates, teacher messages |
| **Brightwheel** | `@brightwheel.com` sender domain | Daily reports, activities, photos |
| **Kumon** | `@kumon.com` sender domain | Learning progress, assignments |
| **Skyward** | `@skyward.com` / `@skyward-sis.com` | Grades, attendance, messages |

Smart parsing works by detecting sender domains in Gmail messages. The email classifier also detects school-direct emails (`.k12.*`, `.edu`, `.org` domains), matches emails to children by name, and flags actionable items with urgency levels.

### Public Sources (auto-discovered)

| Source | How | What it provides |
|---|---|---|
| **School Website** | LLM discovery + crawling | Announcements, news |
| **School Calendar** | ICS/RSS/HTML/PDF discovery | Events, holidays, testing dates, deadlines |

## Digest Pipeline

LangGraph workflow (9 nodes):

1. **fetch_gmail** — Targeted per-child sync (builds queries from search profiles, incremental dedup via `GmailMessageIndex`)
2. **fetch_connectors** — Runs all user-configured platform connectors
3. **fetch_school_sources** — Pulls calendar events, announcements, and doc extractions from verified school sources per child
4. **classify_emails** — Tags Gmail messages by platform (ClassDojo, Brightwheel, etc.), matches to children, flags urgency
5. **parse_pdfs** — Loads uploaded PDF document texts
6. **rag_retrieve** — pgvector similarity search for relevant context
7. **extract_actions** — Extracts due dates, tags, priorities. Tags items with child context.
8. **compose_digest** — **Per-child grouped** using `digest_compose_prompt_v1.md` (falls back to legacy summarize for users without children)

Output: Markdown digest grouped by child with calendar events, action items, announcements, and email highlights. LLM usage metadata stored in the database.

### Targeted Gmail Sync

For each child, the system:
1. Loads the child's `ChildSearchProfile` (known senders, subject keywords, label whitelist, etc.)
2. Builds a targeted Gmail API query: `newer_than:14d ("Vrinda" OR "Cedar Ridge Elementary") (from:@classdojo.com OR from:@brightwheel.com) -category:promotions`
3. Fetches only **new** messages (deduped against `GmailMessageIndex`)
4. Indexes messages for incremental sync (`last_sync_at` tracks progress)
5. Tags digest items with child context for per-child grouping

## Notifications

- Slack-like bell dropdown in the header with unread count badge
- Polls every 30s, shows per-type emoji, time-ago display
- Types: `DIGEST_READY`, `URGENT_EVENT`, `SYSTEM`
- Viewing a digest auto-marks related notifications as read
- Endpoints: `GET /api/notifications`, `GET /api/notifications/unread-count`, `POST /api/notifications/{id}/read`, `POST /api/notifications/mark-all-read`

## Billing

- **Stripe Checkout** for $3/month premium subscription
- **Webhook** handles `checkout.session.completed`, `subscription.updated`, `subscription.deleted`
- **Entitlement enforcement** in `dependencies.py` — returns HTTP 402 when free digests exhausted
- **LLM usage tracking** — records model, tokens, and estimated cost per digest
- **History gating** — Free: 7-day history, Premium: 365-day history

## Database

- **Development**: SQLite (zero config)
- **Production**: Neon Postgres with pgvector extension
- **Migrations**: Alembic (`alembic upgrade head`)
- **Models**: `User`, `Child`, `ChildSearchProfile`, `UserPreference`, `GmailMessageIndex`, `UserIntegration`, `Digest`, `DigestSection`, `DigestItem`, `DigestJob`, `Document`, `Embedding`, `UserEntitlement`, `StripeCustomer`, `LLMUsage`, `Notification`, `DiscoveryJob`, `SchoolSource`

## API Endpoints

### Sources API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/sources/discover` | Start school discovery for a child |
| `GET` | `/api/sources/discover/{job_id}` | Poll discovery job status |
| `GET` | `/api/sources/{child_id}` | List school sources for a child |
| `POST` | `/api/sources/{source_id}/confirm` | Confirm a needs_confirmation source |
| `DELETE` | `/api/sources/{source_id}` | Remove a school source |

### Cron Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/internal/run-daily-digests` | Generate digests for all users |
| `POST` | `/api/internal/refresh-school-sources` | Re-ingest all verified school sources |

## Deployment (Railway)

### Backend service

- **Root directory**: `apps/backend`
- **Start**: `alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port $PORT`
- **Health check**: `/healthz`
- **Cron jobs**:
  - `POST /api/internal/run-daily-digests` with `X-Cron-Secret` header (daily at 6am)
  - `POST /api/internal/refresh-school-sources` with `X-Cron-Secret` header (daily at 4am)

### Frontend service

- **Root directory**: `apps/web`
- **Start**: `npm run start`
- **Framework**: Next.js (auto-detected by Nixpacks)

### Required Railway variables

Set these in each service's Variables tab:

**Backend**: `BACKEND_DATABASE_URL`, `NEXTAUTH_SECRET`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`, `FRONTEND_APP_URL`, `ALLOWED_ORIGINS`, `CRON_SECRET`, `SUPPORT_EMAIL`

**Frontend**: `BACKEND_URL` (internal Railway URL), `NEXTAUTH_SECRET`, `NEXTAUTH_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `NEXT_PUBLIC_APPLE_AUTH_ENABLED`

## Production Notes

- Google OAuth is configured to always show account chooser (`prompt=select_account`).
- Billing checkout and entitlement updates depend on Stripe webhook (`/api/billing/webhook`) events.
- The web app includes `support`, `privacy`, and `terms` pages and uses `support@parently-ai.com` for support communications.
- PWA manifest and `/.well-known/assetlinks.json` are present for PWABuilder/Bubblewrap packaging.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, Tailwind CSS v3, shadcn/ui |
| Auth | NextAuth.js v5 + JWT (HS256 via jose / PyJWT) |
| Backend | FastAPI, Python 3.9+, LangGraph |
| LLM | Gemini 1.5 Flash (primary), GPT-4o-mini (fallback) |
| Database | Neon Postgres + pgvector, SQLAlchemy 2.0 |
| Billing | Stripe (subscriptions + webhooks) |
| Migrations | Alembic |
| PDF | pypdf |
| Web Crawling | httpx, BeautifulSoup4, lxml |
| Calendar | icalendar, feedparser |
| Connectors | google-api-python-client, httpx |
| Deployment | Railway (Nixpacks) |
| Tests | pytest (101 passing) |
