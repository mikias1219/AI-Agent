# Personal AI Agent

One intelligent personal agent that integrates with your digital life — built local-first on
Ubuntu, powered by **Ollama**, starting as a **CLI**, designed to grow into Telegram, REST API,
and web interfaces without rewrites.

## Current status

This is the **foundation** (v0.1): working agent loop, model-provider abstraction
(Ollama + offline fake), controlled tool system with permissions/approvals, SQLite
persistence, personal memory, task management, an audit log, and a CLI.

Integrations (Google Workspace, Telegram, LinkedIn/Facebook), REST API, and scheduled jobs
are **planned, not implemented** — each will be added as an adapter behind existing
contracts (`core/ports.py`, `integrations/`) without reshaping the architecture.
See `docs/architecture.md` for the layer rules and the future-module map.

## Quickstart

```bash
# 1. Environment (Ubuntu)
sudo apt install ollama          # or your usual install path
ollama pull llama3.1:8b          # fits 16 GB RAM comfortably at Q4

# 2. Project
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 3. Configure
cp .env.example .env             # edit as needed

# 4. Run (fake provider needs nothing installed)
personal-agent chat
personal-agent tasks add "Try the agent"
personal-agent tasks list
```

Tests run **without** Ollama, network, or API keys (they use the offline fake provider
and an in-memory SQLite database):

```bash
pytest              # unit + integration + security + e2e
ruff check .        # style gate
ruff format --check .
```

## Layout (tall version)

```
src/personal_agent/
├── core/        # agent loop, contracts (ports), domain types — no I/O, no adapters
├── providers/   # model adapters: ollama, fake (offline, for tests/dev)
├── tools/       # tool specs + registry; THE permission/approval enforcement point
├── integrations/  # external service adapters, added per feature (google, telegram, ...)
├── memory/      # personal memory store (SQLite adapter of MemoryStore port)
├── storage/     # SQLAlchemy models, repositories, Alembic migrations
├── security/    # permissions, approvals, security audit events
├── services/    # application services called by every interface
├── interfaces/  # frontends with zero business logic: cli (+ api, telegram later)
├── config.py, logging_setup.py, bootstrap.py
```

Dependency rule: `interfaces → services → core → ports ← adapters (providers, tools, memory,
storage, integrations)`. `core` never imports adapters; adapters never import interfaces.
