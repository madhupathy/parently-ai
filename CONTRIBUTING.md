# Contributing to Parently AI

Thank you for your interest in Parently AI! This document explains how to contribute to the project.

## Getting Started

1. **Fork** the repository and clone your fork.
2. Create a branch:
   ```bash
   git checkout -b feature/my-feature
   # or
   git checkout -b fix/issue-123
   ```
3. Make your changes and open a **Pull Request** against `main`.

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- SQLite (default for local dev) or Postgres + pgvector (production)

### Backend
```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp env.example .env         # fill in your values
alembic upgrade head
uvicorn app:app --reload --port 8000
```

### Frontend
```bash
cd apps/web
npm install
cp env.example .env.local   # fill in your values
npm run dev
# → http://localhost:3000
```

### Tests
```bash
cd apps/backend
python -m pytest tests/ -v
```

## Database Migrations

Every schema change **must** ship as an Alembic migration:

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

Verify the full chain runs from scratch:
```bash
alembic downgrade base
alembic upgrade head
```

## Code Style

- **Python**: use `ruff` for linting and formatting.
- **TypeScript**: run `npm run lint` in `apps/web/`.
- Follow existing patterns — FastAPI routers in `routers/`, services in `services/`, Pydantic models in `storage/models.py`.

## Security

- **Never** commit `.env` files, API keys, tokens, passwords, Stripe secrets, or OAuth credentials.
- Only add placeholder values to `env.example`.
- If you accidentally expose a secret, rotate it immediately and open an issue.
- `client_secrets.json` and `token.json` are gitignored — never commit them.

## Commit Messages

Use the conventional commits format:
```
feat: add Brightwheel email connector
fix: handle missing child in digest router
docs: update env variable table for SMTP
chore: upgrade langchain to 0.3
```

## Pull Request Checklist

- [ ] `pytest tests/ -v` passes
- [ ] Alembic migration included if schema changed
- [ ] `env.example` updated if new variables were added
- [ ] README updated if new features or endpoints were added
- [ ] No hardcoded secrets, tokens, or API keys

## Reporting Bugs

Open a [GitHub Issue](../../issues/new?template=bug_report.md) with:
- Steps to reproduce
- Expected vs actual behavior
- Python/Node versions, OS, and deployment environment

## License

By contributing, you agree your contributions will be licensed under the project's existing license.
