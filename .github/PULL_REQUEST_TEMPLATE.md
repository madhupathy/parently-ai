## Summary

Briefly describe what this PR does.

## Changes

- 
- 

## Type of change

- [ ] Bug fix
- [ ] New feature / connector
- [ ] Database migration (Alembic)
- [ ] Documentation update
- [ ] Refactor / chore

## Checklist

- [ ] `pytest tests/ -v` passes
- [ ] Alembic migration included (if schema changed)
- [ ] `env.example` updated (if new env vars added)
- [ ] README updated (if behavior changed)
- [ ] No hardcoded secrets, API keys, or passwords
- [ ] Migration chain runs cleanly from empty DB (`alembic downgrade base && alembic upgrade head`)
