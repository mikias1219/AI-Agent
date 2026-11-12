# AURA Personal AI Agent

![evals](docs/badges/eval.svg)

AURA is a single-owner personal AI agent: a Python backend (agent loop, tools,
approvals, audit, persistence), a Next.js dashboard, and two live integrations —
**Telegram** and **Google Workspace** (Gmail, Calendar, Drive). The product scope is
defined in [docs/AURA_PROPOSAL.md](docs/AURA_PROPOSAL.md).

```text
backend/    Agent workflows, tools, auth, persistence, integrations, tests
frontend/   Next.js (App Router) + Tailwind dashboard
docs/       Architecture, deploy guide, ADRs, feature status, design notes
scripts/    Deploy helper and feature-status check
```

## Working now

See the generated [feature status](docs/feature-status.md) (derived from
`frontend/lib/capabilities.ts` and checked in CI).

- Dashboard login, first-owner registration, logout.
- Agent chat with persistent conversation history, a live step trail and a Stop button.
- Agent runs: every turn is a persisted run with events, a prompt version and limits
  (6 tool rounds / 90 s by default). API: `/api/runs` ([ADR 0003](docs/adr/0003-agent-runs-and-event-stream.md)).
- Durable approvals: risky actions pause the run, survive an API restart, expire after 24 h and
  run exactly once when approved (edit-then-approve supported). One approval card in Chat and
  Tasks. API: `/api/approvals` ([ADR 0004](docs/adr/0004-durable-approvals.md)).
- Tasks (agent tools and dashboard management), activity, audit trail.
- Durable scheduler: job queue, reminders (late label after 5 minutes), daily briefing
  automation, Automations screen, and GitHub Actions `tick.yml` calling `/internal/tick`
  ([ADR 0006](docs/adr/0006-durable-scheduler-tick.md)).
- Telegram: token verification, start/stop, live status, allowlisted chats;
  language-independent reply gate, group mention privacy, inline Approve/Deny
  ([ADR 0008](docs/adr/0008-telegram-reply-gate-and-callbacks.md)).
- MCP client (stdio + Streamable HTTP) with Connections UI, allowlist/timeout/size
  caps, and web_search / web_fetch read tools
  ([ADR 0009](docs/adr/0009-mcp-client-without-sdk.md)).
- Offline eval harness (25+ scenarios in CI), lightweight GenAI tracing with
  `trace_id` per run, extended `/api/health`, and Activity run detail + CSV export
  ([ADR 0010](docs/adr/0010-evals-and-lightweight-tracing.md)).
- Google OAuth with server-side sealed tokens; Gmail, Calendar, and Drive read views;
  Read-only switch, search/read/draft/reply and calendar free-slot/delete tools with
  untrusted envelopes ([ADR 0007](docs/adr/0007-google-read-write-scopes.md)).

Not implemented: LinkedIn, Facebook, social publishing, email password recovery, and
the planned modules listed in the feature status (Knowledge, Growth, local worker).
They are shown as placeholders, never simulated.

## Local start

Python 3.11+ and Node.js 22.12+ are required.

```bash
# Backend (from repository root)
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -e './backend[dev]'
cd backend
cp .env.example .env  # first setup only
personal-agent init-dashboard
alembic upgrade head
personal-agent dashboard   # API on http://127.0.0.1:8000
```

```bash
# Frontend (second terminal, from repository root)
npm --prefix frontend ci
npm --prefix frontend run dev   # http://127.0.0.1:3000, /api proxied to the backend
```

Register the single workspace owner in the UI, then open **Connections** for Telegram
and Google. For local inference run Ollama with the model set in `backend/.env`.

## Deploy

Frontend on Vercel, API on Render, Postgres on Supabase, driven by GitHub Actions.
See [docs/deploy.md](docs/deploy.md).

## Guides

- [Architecture](docs/architecture.md) and [ADR 0001](docs/adr/0001-remove-hub-and-social-mocks.md)
- [Feature status](docs/feature-status.md)
- [Cloud deploy](docs/deploy.md)
- [Hermes integration](docs/hermes.md)
- [Backend setup and recovery](backend/README.md)
- [Frontend development](frontend/README.md)
- [Project structure and naming](docs/project-structure.md)

## Verification

Backend, from `backend/` with the virtualenv active:

```bash
python -m pytest
ruff check .
ruff format --check .
```

Frontend and docs, from repository root:

```bash
npm --prefix frontend run format:check
npm --prefix frontend run build
node scripts/check-feature-status.mjs
```

Tests are offline: fake model providers, temporary databases, mocked HTTP.
Never commit `.env` files or secrets.
