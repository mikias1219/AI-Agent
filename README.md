# Personal AI Agent

A local-first personal agent with a Python backend, React + Tailwind dashboard,
and Telegram as its first external channel.

```text
backend/    Agent workflows, tools, authentication, persistence, integrations, tests
frontend/   React UI and browser tests
docs/       Architecture, naming conventions, specifications, design reviews
```

## Working now

- Real local dashboard login, first-owner registration, and logout.
- Ollama-backed agent chat with persistent conversation history.
- Telegram token verification, dashboard start/stop controls, live status, reply
  activity, blocked-chat discovery, and conversation history.
- Task tools for the agent, plus task management in the dashboard.
- Permission checks, human approvals, audit activity, and personal memory.

Google Workspace, LinkedIn, Facebook, social publishing, and email password recovery
are not implemented yet. Content Studio is marked planned rather than simulating posts.

## Start

Python 3.11+ and Node.js 22.12+ are required. From repository root:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -e './backend[dev]'
npm --prefix frontend ci
npm --prefix frontend run build
cd backend
cp .env.example .env  # first setup only; keep an existing configured .env
personal-agent init-dashboard
alembic upgrade head
personal-agent dashboard
```

Open `http://127.0.0.1:8000`. Existing environment-based dashboard passwords still
work. Otherwise register the single local workspace owner. For real inference,
run Ollama and install the model configured in `backend/.env`.

Open Telegram in the dashboard sidebar to verify, start, and test your bot. Only
allowlisted chats receive replies. Google/social apps remain visibly planned.

Backend settings and SQLite data live under `backend/`. Existing root virtual
environments can stay where they are; activate one and reinstall `./backend[dev]`
rather than moving it. Restart older backend processes after source changes.

## Guides

- [Backend setup, Telegram, and recovery](backend/README.md)
- [Frontend development and browser tests](frontend/README.md)
- [Project structure and naming](docs/project-structure.md)
- [Architecture](docs/architecture.md)
- [Original dashboard design](docs/design/dashboard.md)

## Verification

With the Python environment activated, from `backend/`:

```bash
python -m pytest
ruff check .
ruff format --check .
```

From repository root:

```bash
npm --prefix frontend run build
npm --prefix frontend run format:check
npm --prefix frontend run test:e2e
```

Browser tests use an isolated backend, fake model, and mocked Telegram transport.
They require an installed Playwright Chromium browser or an explicit local browser
path; see the frontend guide. No real Telegram messages are sent by the test suite.
