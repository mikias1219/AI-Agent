# Repository structure and naming conventions

`backend/` owns agentic execution and persistence. `frontend/` owns the Next.js UI.
`docs/` owns architecture, product specifications, and design reviews. This project
uses a layered Python backend and a feature-organized React frontend.

## Backend

```text
backend/
├── src/personal_agent/
│   ├── app/
│   │   └── container.py                  # Dependency wiring and application container
│   ├── config/
│   │   ├── settings.py                   # Environment-driven settings
│   │   └── logging.py                    # Log configuration and redaction
│   ├── domain/                          # Framework-independent rules and contracts
│   │   ├── models.py                     # Domain dataclasses, enums, value objects
│   │   ├── exceptions.py                 # Shared domain/application error vocabulary
│   │   ├── ports.py                      # Protocols implemented by adapters
│   │   ├── task_rules.py                 # Task creation and legal state transitions
│   │   └── conversation.py               # Conversation context helpers
│   ├── application/                     # Agentic execution and use cases
│   │   ├── agent.py                      # Model/tool orchestration loop
│   │   ├── services/
│   │   │   ├── chat_service.py
│   │   │   ├── task_service.py
│   │   │   ├── auth_service.py
│   │   │   └── telegram_service.py
│   │   ├── security/                     # Approval workflow, permissions, audit helpers
│   │   └── tools/
│   │       ├── registry.py               # Controlled tool execution gate
│   │       ├── decorators.py             # Tool definition decorator
│   │       └── builtins/                 # Utility and task tools
│   ├── infrastructure/                  # Concrete I/O adapters
│   │   ├── model_providers/
│   │   │   ├── base.py                   # Provider config, retries, serialization helpers
│   │   │   ├── ollama_provider.py
│   │   │   └── fake_provider.py
│   │   ├── persistence/
│   │   │   ├── database.py               # Engine and session lifecycle
│   │   │   ├── models.py                 # ORM rows (distinct from domain models)
│   │   │   ├── repositories.py
│   │   │   ├── account_repository.py
│   │   │   └── memory_store.py
│   │   └── integrations/
│   │       └── telegram/
│   │           ├── client.py             # Telegram HTTP transport
│   │           ├── mapper.py             # External payload → internal message mapping
│   │           ├── runner.py             # Polling and message routing
│   │           ├── exceptions.py         # Telegram-specific failures
│   │           └── worker.py             # Dashboard-owned start/stop lifecycle
│   └── presentation/                    # Entry points and interface adapters
│       ├── cli/main.py
│       ├── telegram/main.py
│       └── web/app.py                    # API, session gate, React build serving
├── migrations/                         # Alembic migration environment and versions
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   ├── e2e/
│   ├── evaluation/
│   └── conftest.py
├── .env.example
├── alembic.ini
├── pyproject.toml
└── README.md
```

Python packages and files use `snake_case`. Classes use `PascalCase`; constants use
`UPPER_SNAKE_CASE`; functions and variables use `snake_case`. Test modules use
`test_<responsibility>.py`. Package markers (`__init__.py`) do not re-export whole
layers or hide dependency directions. `personal_agent` remains the import namespace;
`personal-agent` remains the installed command.

The two `models.py` files have different owners: domain models describe application
concepts, while persistence models describe database rows. Conversions belong in the
persistence adapter. External service adapters live under
`infrastructure/integrations/<service>/` when actually implemented.

## Frontend

```text
frontend/
├── app/                # Next.js App Router: (auth) login/register, (app) pages
├── components/         # Shell (sidebar, header, drawers) and shared UI
├── features/           # activity, auth, chat, connections, overview, settings, tasks
├── lib/                # api/ client, auth helpers, capabilities.ts
├── styles/tokens.css   # Design tokens
├── next.config.ts
├── vercel.json         # Production /api rewrite to Render
├── package.json
└── README.md
```

React component files use `kebab-case.tsx` with `PascalCase` exports; hooks start with
`use`. A feature owns its pages, components, and hooks; only cross-feature code belongs
in `components/` or `lib/`. Create subfolders only when they contain real code.

## Dependency boundaries

- Backend domain depends on standard-library/domain code only.
- Backend application depends on domain contracts and other application modules.
- Infrastructure implements those contracts and can call application services at
  inbound integration boundaries, such as the Telegram runner.
- `app/container.py` wires concrete implementations together.
- Presentation handles requests/input/output and starts the configured application.
- Frontend feature code may use `shared`; `shared` does not depend on features or app.
- The Next.js app calls the backend over same-origin `/api` (rewritten by Next locally
  and by `vercel.json` in production). The backend exposes the API only.
- Auth, Telegram, and Google are working features; LinkedIn/Facebook and social
  publishing are not implemented. Feature honesty is tracked in
  [feature-status.md](feature-status.md).

## Configuration and runtime data

Run backend commands from `backend/`: the settings loader reads `.env` from the
working directory and the default SQLite URL resolves to `backend/data/agent.db`.
Existing configuration and database contents are preserved there. User-supplied
absolute paths or custom database URLs remain unchanged.

Real `.env` files, databases, virtual environments, Python caches,
`frontend/node_modules/`, and generated builds are ignored. New Python environments
belong at `backend/.venv/`; an existing root `.venv/` can remain in place to preserve
its executable paths. Reinstall the backend after changing package entry points.

## Commands

From the repository root, with the backend environment activated:

```bash
python -m pip install -e './backend[dev]'
npm --prefix frontend ci
npm --prefix frontend run dev
npm --prefix frontend run build
npm --prefix frontend run format:check
```

From `backend/`:

```bash
python -m pytest
personal-agent telegram
personal-agent dashboard
alembic history
```

The root README links to each application's setup guide. Design specifications and
review images stay in `docs/design/`; executable application code stays out of docs.
