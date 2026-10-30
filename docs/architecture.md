# Architecture

One local-first personal agent serves CLI, Telegram, and the existing authenticated
local dashboard. The React + Tailwind frontend is served by the backend dashboard.
Google Workspace and social publishing remain planned.

## Backend layers

```text
presentation/                 CLI, Telegram launcher, FastAPI dashboard
    │ starts/calls
app/container.py              Composition root that wires adapters to contracts
    │
application/                  Agent loop, services, tools, approval workflow
    │ depends on
domain/                      Models, contracts, exceptions, task rules
    ▲
infrastructure/               Providers, persistence, external-service adapters
```

Domain code contains no framework/database/network imports. Application code depends
on domain contracts rather than concrete providers or repositories. Infrastructure
implements I/O details. An inbound integration runner can orchestrate application
services; it is not imported by the domain or application layers. Presentation owns
request parsing, responses, and launchers. Configuration lives in `config/`.

`app/container.py` is the place that knows concrete implementations and wires them
into the shared application. It does not contain agent decisions or business rules.

## Contracts

`domain/ports.py` defines `ModelProvider`, `ToolRegistry`, `MemoryStore`,
`ConversationRepository`, `TaskRepository`, `ApprovalGateway`, and `AuditLog`.
The approval repository protocol is local to `application/security/approvals.py`.

Tool execution goes through `application/tools/registry.py`, which checks permission
policy, validates input, consults the approval gateway, and records audit events.
The model never grants itself permission. Application services orchestrate persistence
through contracts, while `infrastructure/persistence/` owns SQLAlchemy and SQLite.
Domain models remain separate from ORM rows.

## Interfaces and persistence

- CLI entry point: `personal_agent.presentation.cli.main:main`.
- Telegram launcher: `presentation/telegram/main.py`.
- Telegram polling/transport: `infrastructure/integrations/telegram/`.
- Web API: `presentation/web/app.py`, serving `frontend/dist/` and its `/assets/`.
- Migration environment and versions: `backend/migrations/`.
- Settings: `config/settings.py`, loading the working directory's `.env`.

Run backend commands from `backend/`. SQLite remains local, and existing runtime data
stays under `backend/data/`. SQLAlchemy repositories and Alembic support later database
changes without coupling domain types to database rows.

## Frontend boundary

`frontend/src/app/` composes routes, authenticated loading, and the shell.
`frontend/src/features/` owns auth, home, chat, Telegram, tasks, connections, activity,
and the planned content studio. `frontend/src/shared/` owns UI, API transport, hooks,
metadata, and Tailwind styles. Requests use same-origin `/api`; the Vite development
server proxies those requests to the backend.

Registration creates a single local workspace owner with a salted password hash.
Existing environment-configured passwords remain supported. Sessions use signed,
HTTP-only cookies; changing credentials invalidates existing signatures. Registration
closes once an owner exists. Local password recovery is a CLI command, not an email flow.

The composition root creates a Telegram worker sharing the same chat service, tools,
approval gateway, and database as dashboard chat. It starts only after an authenticated
start request and receives a stop event on shutdown. Its persisted audit heartbeats
let the UI distinguish listening, answering, errors, stopped, and expired status.
An external CLI bot remains independently controlled. Chat identities use numeric
sender/chat IDs; recent conversation IDs are recovered from repositories on restart.

Google/social integrations and social publishing are deferred. The active Content
Studio page states this directly. Backend permission, approval, and audit enforcement
remains authoritative regardless of which interface initiates a request.

## Extensions

| Capability | Owner when implemented |
| --- | --- |
| Google Workspace | `infrastructure/integrations/google/` |
| LinkedIn and Facebook | `infrastructure/integrations/{linkedin,facebook}/` |
| Hosted model providers | `infrastructure/model_providers/` |
| New user interfaces/API endpoints | `presentation/` |
| Agentic workflows | `application/` using domain contracts |
| Retrieval and memory adapters | `infrastructure/` implementing `MemoryStore` |
| Schema evolution | `backend/migrations/versions/` |

Tests remain offline: fake providers, temporary SQLite, and mocked HTTP transports.
See [project structure](project-structure.md) for filenames, naming rules, and commands.
