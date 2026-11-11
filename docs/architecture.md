# Architecture

AURA is one personal agent reachable from the Next.js dashboard, Telegram, and the CLI.
The Python backend is the control plane and enforces permissions, approvals, and audit
regardless of which interface initiates a request. Live integrations are **Telegram**
and **Google Workspace**; everything else is planned (see
[feature status](feature-status.md)).

```text
Browser ── Next.js (Vercel) ── /api rewrite ──► FastAPI (Render) ──► Supabase Postgres
                                                   │
                                                   ├── Telegram worker
                                                   ├── Google OAuth + Gmail/Calendar/Drive
                                                   └── Model provider (Ollama / Hermes / OpenAI-compatible)
```

## Backend layers

```text
presentation/                 CLI, Telegram launcher, FastAPI app
    │ starts/calls
app/container.py              Composition root that wires adapters to contracts
    │
application/                  Agent loop, services, tools, approval workflow
    │ depends on
domain/                       Models, contracts, exceptions, task rules
    ▲
infrastructure/               Providers, persistence, Telegram and Google adapters
```

Domain code has no framework, database, or network imports. Application code depends
on domain contracts. Infrastructure implements I/O. `app/container.py` is the only
place that knows concrete implementations. Configuration lives in `config/`.

## Contracts and tool safety

`domain/ports.py` defines `ModelProvider`, `ToolRegistry`, `MemoryStore`,
`ConversationRepository`, `TaskRepository`, `ApprovalGateway`, and `AuditLog`.
Tool execution goes through `application/tools/registry.py`, which checks permission
policy, validates input, consults the approval gateway, and records audit events.
The model never grants itself permission.

## Interfaces and persistence

- CLI: `personal_agent.presentation.cli.main:main`.
- Web API: `presentation/web/app.py` (`/api/*`: auth, chat, tasks, activity, status,
  Telegram, Google).
- Telegram: `infrastructure/integrations/telegram/`; the worker shares the chat
  service, tools, approvals, and database with dashboard chat, and starts only after an
  authenticated start request.
- Google: `infrastructure/integrations/google/` (OAuth, sealed token storage, Gmail,
  Calendar, and Drive clients).
- Persistence: SQLAlchemy repositories with Alembic migrations in
  `backend/migrations/`. SQLite locally, Supabase Postgres in production.
- Settings: `config/settings.py`, loading `.env` from the working directory.

Registration creates a single workspace owner with a salted password hash. Sessions
use signed, HTTP-only cookies. Registration closes once an owner exists.

## Frontend

`frontend/` is a Next.js App Router app with Tailwind CSS v4:

- `app/` — routes (`(auth)` login/register, `(app)` overview, chat, tasks, activity,
  connections, settings) and the auth gate.
- `features/` — page modules; `components/` — shell and shared UI; `lib/` — API
  client, auth helpers, and `capabilities.ts`.
- Requests use same-origin `/api`: Next rewrites to the backend locally
  (`PERSONAL_AGENT_BACKEND_URL`), and `vercel.json` rewrites to Render in production.
- `lib/capabilities.ts` marks each feature `api` or `mock`. The UI must not present a
  `mock` feature as working; `scripts/check-feature-status.mjs` enforces this in CI.
  The local worker is not connected and the UI must not invent worker or model activity.

Modules without a backend (Inbox, Memory, Knowledge, Growth, Automation) render
explicit placeholders.

## Inference

Local development uses Ollama, optionally through the Hermes runtime (needs at least
64k context against a local Ollama URL; otherwise the Ollama agent loop is used and
`/api/status` reports `active_runtime` / `runtime_reason`). Production uses
`PERSONAL_AGENT_PROVIDER=openai` against an OpenAI-compatible endpoint configured by
`HERMES_*` or `OPENAI_COMPAT_*` secrets. See [hermes.md](hermes.md).

## Extension points

| Capability | Owner when implemented |
| --- | --- |
| New channels (e.g. LinkedIn, Facebook) | `infrastructure/integrations/<name>/` |
| Model providers | `infrastructure/model_providers/` |
| API endpoints / interfaces | `presentation/` |
| Agent workflows | `application/` using domain contracts |
| Memory and retrieval | `infrastructure/` implementing `MemoryStore` |
| Schema changes | `backend/migrations/versions/` |

Decisions are recorded in [adr/](adr/). Tests stay offline: fake providers, temporary
databases, mocked HTTP transports. See [project-structure.md](project-structure.md).
