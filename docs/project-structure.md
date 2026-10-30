# Repository structure and naming conventions

`backend/` owns agentic execution and persistence. `frontend/` owns the React UI.
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
├── src/
│   ├── app/
│   │   ├── App.jsx                       # Authenticated page composition
│   │   ├── useWorkspaceData.js            # Backend loading/polling
│   │   ├── layouts/DashboardLayout.jsx   # Persistent dashboard shell
│   │   └── routing/
│   │       ├── navigation.js             # Route IDs and navigation metadata
│   │       └── useHashRoute.js
│   ├── features/
│   │   ├── auth/pages/AuthenticationPage.jsx
│   │   ├── home/pages/HomePage.jsx
│   │   ├── chat/                         # Chat page and useAgentChat hook
│   │   ├── connections/pages/ConnectionsPage.jsx
│   │   ├── activity/pages/ActivityPage.jsx
│   │   ├── telegram/pages/TelegramPage.jsx
│   │   ├── tasks/pages/TasksPage.jsx
│   │   └── content-studio/pages/ContentStudioPage.jsx # Planned feature
│   ├── shared/
│   │   ├── components/ui/                # Brand, Avatar, AppMark, PageHeading, Toast
│   │   ├── config/app-catalog.js          # Display metadata, not live account state
│   │   ├── api/client.js                 # Same-origin API transport
│   │   ├── hooks/useNotification.js
│   │   └── styles/globals.css            # Tailwind theme and shared compositions
│   └── main.jsx                          # React mount point
├── index.html
├── package.json
├── package-lock.json
├── vite.config.js
├── playwright.config.js
├── tests/                              # Browser tests and isolated backend fixture
└── README.md
```

React component files and exports use `PascalCase`. Hooks use `useCamelCase` and
start with `use`. Feature folders and ordinary JS data/config filenames use
`kebab-case`; ordinary functions/variables use `camelCase`. A feature owns its pages,
components, hooks, and sample data. Only cross-feature presentation and behavior
belong in `shared/`. The app composes features; shared code does not import features.
Create subfolders only when they contain real code, rather than adding empty API,
asset, store, or integration folders in anticipation of future work.

## Dependency boundaries

- Backend domain depends on standard-library/domain code only.
- Backend application depends on domain contracts and other application modules.
- Infrastructure implements those contracts and can call application services at
  inbound integration boundaries, such as the Telegram runner.
- `app/container.py` wires concrete implementations together.
- Presentation handles requests/input/output and starts the configured application.
- Frontend feature code may use `shared`; `shared` does not depend on features or app.
- React calls the backend over `/api`. The backend serves the built frontend; it no
  longer owns duplicate HTML/CSS/JS dashboard sources. Without a frontend build,
  the page returns a clear build instruction while API endpoints remain available.
- Auth and Telegram lifecycle are working features; Google and social publishing
  remain planned. Static app metadata is never treated as a connection-health result.

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
