# AURA frontend (Next.js)

Next.js App Router UI with Tailwind CSS v4. It is the production UI (deployed to
Vercel) and talks to the Python backend over same-origin `/api`.

## Requirements

- Node.js **22.12+**
- Backend on **http://127.0.0.1:8000** (or set `PERSONAL_AGENT_BACKEND_URL`)

## Local development

```bash
# Terminal 1 — backend (Python env active)
cd backend
personal-agent dashboard
```

```bash
# Terminal 2 — frontend, from repository root
npm --prefix frontend ci
npm --prefix frontend run dev
```

Open **http://127.0.0.1:3000**. `next.config.ts` rewrites `/api/*` to the backend. In
production `vercel.json` rewrites `/api/*` to Render.

### Environment variables

Copy `frontend/.env.example` to `frontend/.env.local` when needed:

| Variable                     | Purpose                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------ |
| `PERSONAL_AGENT_BACKEND_URL` | Rewrite target for `/api` during `next dev` / `next build`                     |
| `NEXT_PUBLIC_API_BASE_URL`   | Optional absolute API base; leave empty so the browser uses same-origin `/api` |

If the backend is down, pages show real connection errors; there is no demo fallback.

## Auth

- **Register** creates the single workspace owner (when the backend allows it).
- **Login** sets an HTTP-only session cookie via `/api/auth/*`.
- **Sign out** clears the session from the header profile menu.

## Capability flags

`lib/capabilities.ts` declares each feature as `api` (live backend) or `mock`. Docs are
checked against it:

```bash
node scripts/check-feature-status.mjs          # verify (runs in CI)
node scripts/check-feature-status.mjs --write  # regenerate docs/feature-status.md
```

Current status lives in [docs/feature-status.md](../docs/feature-status.md). A `mock`
feature must never be presented as available.

## Checks and build

```bash
npm --prefix frontend run format:check
npm --prefix frontend run build
npm --prefix frontend run start   # serve the production build on :3000
```

## Source layout

- `app/` — routes, layouts, auth gate
- `components/` — shell (sidebar, header, drawers) and shared UI
- `features/` — page modules (overview, chat, tasks, activity, connections, settings, auth)
- `lib/` — API client, auth helpers, capabilities
- `styles/tokens.css` — design tokens
