# Contributing to AURA

## Source of truth

Product scope lives in [`docs/AURA_PROPOSAL.md`](docs/AURA_PROPOSAL.md). Requirement IDs (FND, AGT, APR, TSK, MEM, INT, AUT, UX, OBS, NFR) and business rules BR-01..BR-14 decide what ships. Do not expand scope beyond the prompt for a change.

## Local checks

From `backend/` (venv active):

```bash
python -m pytest
ruff check .
ruff format --check .
mypy src/personal_agent/domain src/personal_agent/application
```

From `frontend/`:

```bash
npm run format:check
npx tsc --noEmit
npm run build
npm test
```

## Conventions

- Conventional commits (`feat:`, `fix:`, `docs:`, …).
- One ADR per significant decision under `docs/adr/`.
- Every schema change needs an Alembic migration that works on SQLite and Postgres.
- Tools go through `ToolRegistry.execute` with an `access_kind`.
- No mock data outside demo mode (`/demo` + `DEMO_DATABASE_URL`).
- Never commit secrets or `.env` files.

## Pull requests

Use the checklist in the proposal (Part 3 §21): requirement IDs, approvals, untrusted content, loading/empty/error states, migrations, and AGENTS.md checks.
