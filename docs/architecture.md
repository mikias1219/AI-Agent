# Architecture

## Principles

1. Modular monolith — one deployable/local app, strictly separated internal layers.
2. All external boundaries behind contracts. `core/ports.py` (Protocols) is the hinge.
3. Security is application code: permissions and approvals are enforced in
   `tools/registry.py` (the *only* execution gate), never delegated to the model.
4. Tests require no Ollama, no network, no API keys.

## Dependency flow

```text
interfaces (cli ── later: api, telegram, web)
    │ calls only
services (chat, task)                    # use-case orchestration, persistence boundaries
    │ uses
core (agent, conversation, tasks, types) # depends ONLY on core/ports.py
    ▲                                     ▲
    │ implements                          │ enforced-at-execution calls into
providers (ollama, fake)     tools/registry ──▶ security/permissions + approvals
memory (sqlite)                           └─▶ security/audit ──▶ storage/audit_repo
storage (db, repositories, migrations)    # only layer touching the database
integrations (added per feature)          # own their clients, auth, mapping, errors
```

Hard rules:

- `core` never imports providers, storage, integrations, or interfaces.
- `interfaces` never import providers, direct handlers, or DB layer — only services.
- Tool execution happens **only** through `tools/registry.execute`, which checks
  `security/permissions.py`, consults the approval gateway for `execute`-kind tools
  (no permissive shortcuts), and records decisions in the audit log.
- Registry specs are delivered to providers through `tools/base.ToolSpec` contract shape.

## Contracts in `core/ports.py`

`ModelProvider` · `ToolRegistry` · `MemoryStore` · `ConversationRepository`
`TaskRepository` · `ApprovalGateway` · `AuditLog`. Future integrations declare their
own contracts locally (see `integrations/__init__.py` note) to keep the core untouched.

## Now vs. later

Implemented in v0.1: agent loop with tool calling, Ollama + fake providers, tool registry
with permissions/approvals/audit, SQLite storage with Alembic, memory store, task domain,
Chat/Task services, CLI, full test suite (unit/integration/security/e2e).

Deferred (add as adapters without reshaping anything):

| Capability            | Where it will live                        |
| --------------------- | ----------------------------------------- |
| Google integrations   | `integrations/google/*`                   |
| Social platforms      | `integrations/{linkedin,telegram}/*`      |
| REST API / Telegram / Web | `interfaces/{api,telegram_bot,web}`   |
| Hosted model provider | `providers/<vendor>.py`                   |
| Vector retrieval      | `memory/<store>.py` implementing `MemoryStore` |
| Scheduler / jobs      | `jobs/` (only when a real recurring need) |
| Workflow engine       | `core/workflows.py`                       |
| Evaluation testing    | `tests/evaluation/`                       |

## Known trade-offs

- Protocol ports add slight indirection vs. direct imports — accepted cost for provider/
  storage/integration independence.
- ORM models are deliberately separate from `core/types.py`; mappers in
  `storage/repositories.py` prevent the DB schema from becoming the domain.
- `sqlite3` would be lighter than SQLAlchemy, but PostgreSQL migration readiness
  (stated requirement) makes SQLAlchemy + Alembic the justified choice.
