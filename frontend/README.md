# Personal Agent frontend

React + Tailwind CSS v4, connected to the Python agent backend. The backend serves
this frontend's production build; all application requests use same-origin `/api`.

## Run the complete application

From the repository root:

```bash
npm --prefix frontend ci
npm --prefix frontend run build
```

With the backend Python environment activated:

```bash
cd backend
personal-agent init-dashboard
personal-agent dashboard
```

Open `http://127.0.0.1:8000`. Existing environment-based passwords continue to work.
If no owner/password is configured, register the single local owner from the UI.
Registration stores a salted password hash in SQLite; sessions use HTTP-only cookies.

## Frontend development

Start the backend on port 8000 in one terminal. In another, from repository root:

```bash
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to the backend, preserving cookies.
The frontend displays a connection error if the backend is unavailable; it does not
fall back to demo data. Node.js 22.12+ is required.

## Implemented screens

- Home: real agent requests, Telegram configuration summary, task count.
- My agent: streamed model-backed chat, persistent history, and live approvals during tool calls.
- Telegram: verify the token, start/stop the dashboard's bot, monitor heartbeats,
  read reply activity, find blocked chat IDs, and open Telegram conversations.
- Tasks & approvals: create tasks, apply valid state transitions, and decide actions.
- Connected apps: actual Telegram configuration; Google/social integrations marked planned.
- Activity: real audit events, details, and pagination.
- Authentication: login, first-owner registration, logout, and local recovery guidance.

Content Studio is explicitly planned. It no longer generates example posts or simulates
publishing. Google Workspace, LinkedIn, Facebook, and email password recovery are not
implemented.

## Browser tests

Tests launch a real backend with a temporary database, fake model, and mocked Telegram
transport. They do not use real tokens, local production data, or external accounts.

With the backend environment activated (so `python` imports `personal_agent`):

```bash
npm --prefix frontend exec -- playwright install chromium
npm --prefix frontend run test:e2e
```

Set `BACKEND_PYTHON` to an absolute Python executable when not using an activated
environment. Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to an installed Chrome/Chromium
executable to reuse a local browser. Test traces are retained on failure.

```bash
npm --prefix frontend run build
npm --prefix frontend run format:check
```

## Source layout

`src/app/` owns composition, routing, shared loading state, and the dashboard layout.
`src/features/` owns auth, home, chat, Telegram, tasks, connections, activity, and the
planned content-studio page. `src/shared/` owns reusable UI, API transport, hooks,
app metadata, and Tailwind styles. Browser tests and their isolated backend fixture
live in `tests/`. See [the structure guide](../docs/project-structure.md).
