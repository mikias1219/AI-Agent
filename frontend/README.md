# Personal Agent frontend (Next.js)

Next.js App Router UI with Tailwind CSS v4, talking to the Python agent backend over `/api`.
This branch replaces the old Vite app for local development on port **3000**. **Production
Vercel/CI cutover is not included** — deploy wiring (`vercel.json`, GitHub Actions, Render)
is unchanged elsewhere in the repo.

## Requirements

- Node.js **22.12+**
- Backend listening on **http://127.0.0.1:8000** (or set `PERSONAL_AGENT_BACKEND_URL`)

## Local development

From the repository root:

```bash
# Terminal 1 — backend (with your Python env active)
cd backend
personal-agent dashboard
```

```bash
# Terminal 2 — frontend
npm --prefix frontend ci
npm --prefix frontend run dev
```

Open **http://127.0.0.1:3000**. Next.js rewrites `/api/*` to the backend (`next.config.ts` uses
`PERSONAL_AGENT_BACKEND_URL`, default `http://127.0.0.1:8000`).

### Environment variables

Copy `frontend/.env.example` to `frontend/.env.local` when needed:

| Variable                     | Purpose                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------ |
| `PERSONAL_AGENT_BACKEND_URL` | Rewrite target for `/api` during `next dev` / `next build`                     |
| `NEXT_PUBLIC_API_BASE_URL`   | Optional absolute API base; leave empty so the browser uses same-origin `/api` |

If the backend is down, pages show real connection errors — there is no demo fallback data.

## Auth

- **Register** creates the single local owner (when allowed by the backend).
- **Login** sets an HTTP-only session cookie via `/api/auth/*`.
- **Sign out** clears the session from the header profile menu.

## Capability flags

`lib/capabilities.ts` documents what is live vs preview:

| Key                                     | Mode                 |
| --------------------------------------- | -------------------- |
| `chat`, `tasks`, `activity`, `telegram` | `api` (live backend) |
| `google`                                | `api` when connected |

## Production build (local check)

```bash
npm --prefix frontend run build
npm --prefix frontend run start
```

The backend can still serve a static build from its own pipeline; this README only covers the
Next.js dev loop.

## Source layout

- `app/` — routes, layouts, auth gate
- `components/` — shell (sidebar, header, drawers) and shared UI
- `features/` — page modules (overview, chat, tasks, activity, connections, settings, auth)
- `lib/` — API client, auth helpers, capabilities, mocks
- `styles/tokens.css` — design tokens

The legacy Vite Playwright suite (`playwright.config.js` and `tests/e2e/`) has been removed.
`tests/fixtures/` is not used by the Next.js app.
