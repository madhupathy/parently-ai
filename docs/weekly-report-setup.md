# Weekly ops report — setup

A GitHub Action runs every Monday at 09:00 UTC and emails `madhupathy@gmail.com` with:

- User count + new users this week
- Premium subscriber count
- Digest run count
- LLM cost (real, from the `llm_usage` table)
- Infra cost (monthly figures from `apps/backend/config/infra_costs.yaml`)
- Rough MRR + burn-rate status

Files:

- `apps/backend/scripts/weekly_report.py` — the script (also runnable locally with `--dry-run`)
- `.github/workflows/weekly-report.yml` — the cron
- `apps/backend/config/infra_costs.example.yaml` — copy to `infra_costs.yaml` and edit

## One-time setup

1. **Copy the costs template into the real file** (not gitignored — you may want it tracked so the report stays reproducible):

   ```
   cp apps/backend/config/infra_costs.example.yaml apps/backend/config/infra_costs.yaml
   ```

   Update the dollar amounts as bills arrive.

2. **Add these GitHub repo secrets** (`Settings → Secrets and variables → Actions`):

   | Secret | Value |
   |---|---|
   | `BACKEND_DATABASE_URL` | Neon Postgres URL (read-only role recommended) |
   | `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | Whatever provider you use for digest delivery — same creds work |
   | `SMTP_FROM` | e.g. `ops@parently-ai.com` |
   | `SMTP_SECURE` | `true` or `false` matching your provider |
   | `NEXTAUTH_SECRET` | Backend already requires this for config import; any non-empty value works for the script |

3. **Test it manually** before relying on the cron:

   ```
   gh workflow run weekly-report.yml
   ```

   Or locally:

   ```
   cd apps/backend
   pip install -r requirements.txt pyyaml
   BACKEND_DATABASE_URL=... python scripts/weekly_report.py --dry-run
   ```

## What the report can't see (yet)

- **Railway, Neon, registrar bills** don't have first-class billing APIs we can query without a paid integration. The script uses the YAML config you maintain monthly.
- **Stripe fees**: not pulled from Stripe API. Once MRR is meaningful, we could add a Stripe pull, but it's not worth the complexity at $0 MRR.
- **Gemini API spend**: the cheapest source of truth is the `LLMUsage.estimated_cost_usd` column, which the digest pipeline writes after every call. That's already in the report — no need to call Google's billing API.

## Failure modes worth knowing

- **SMTP misconfigured** → workflow logs will show `RuntimeError: SMTP_HOST and SMTP_FROM must be set` and the run is marked failed; GitHub will email you about the failed run.
- **DB unreachable** → SQLAlchemy traceback in logs. The script does not retry; you'll get a failed-run notice from GitHub.
- **Empty database** → all metrics will be 0 and a $0.00 report still sends. That's the right behavior.
