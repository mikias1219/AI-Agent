# Cloud deploy (Vercel + Render + Supabase)

Production layout:

- **Frontend** → Vercel (`frontend/`)
- **Backend** → Render Docker service (`backend/Dockerfile`, `render.yaml`) — control plane
- **Database** → **new** Supabase Postgres project (do not reuse the Shop Mini App DB)
- **Model** → **Local Ollama only** (on your Ubuntu machine). No paid cloud model APIs.
- **Secrets** → GitHub Environment `production` only; Actions sync them to Render/Vercel

Until Phase 3 (local worker), the Render dyno cannot reach your laptop Ollama. The
blueprint defaults `PERSONAL_AGENT_PROVIDER=fake` on Render so the API stays up without
calling external model providers. Real inference runs locally via `personal-agent dashboard`.

## One-time platform setup

### 1. Supabase (new project)

1. Create a project at [supabase.com](https://supabase.com).
2. Copy the **pooler** connection string (Settings → Database).
3. Store it as GitHub secret `DATABASE_URL` (either `postgresql://…` or `postgres://…`; the app normalizes to `postgresql+psycopg://`).

### 2. Local inference (not on Render)

Run Ollama on your Ubuntu machine for real answers. Optional Hermes: see
[hermes.md](hermes.md). Do not configure OpenRouter or other paid model APIs.

### 3. Render

1. Connect this GitHub repo and create a web service from `render.yaml` (Docker).
2. Note the service id (Dashboard → service → Settings) → `RENDER_SERVICE_ID`.
3. Create an API key → `RENDER_API_KEY`.
4. After first deploy, copy the service URL and put it in `frontend/vercel.json` as the
   `/api/:path*` rewrite destination (so the SPA stays same-origin and session cookies work).

### 4. Vercel

1. Import the repo; set **Root Directory** to `frontend`.
2. Run once locally (or use the dashboard) to capture ids:

   ```bash
   cd frontend
   npx vercel link
   ```

3. Store `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.
4. After the first production URL exists, set `FRONTEND_ORIGIN` to that origin (e.g. `https://your-app.vercel.app`).
5. Leave `VITE_API_BASE_URL` **empty** — the Vercel rewrite proxies `/api` to Render.

### 5. Dashboard signing + Telegram

1. Generate a long secret (≥ 32 chars) → `DASHBOARD_SECRET_KEY`.
2. Optional: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_CHAT_IDS` (comma-separated chat ids).

### 6. GitHub Environment

In the GitHub repo → Settings → Environments → **production**, add:

| Secret | Purpose |
| --- | --- |
| `DATABASE_URL` | Supabase pooler URL |
| `DASHBOARD_SECRET_KEY` | Session signing |
| `FRONTEND_ORIGIN` | Vercel origin for CORS |
| `VITE_API_BASE_URL` | Optional; leave empty for same-origin `/api` proxy |
| `TELEGRAM_BOT_TOKEN` | BotFather token |
| `TELEGRAM_ALLOWED_CHAT_IDS` | Allowlist |
| `VERCEL_TOKEN` / `VERCEL_ORG_ID` / `VERCEL_PROJECT_ID` | Frontend deploy |
| `RENDER_API_KEY` / `RENDER_SERVICE_ID` | Backend env sync + deploy |

Chicken-and-egg for first deploy: create Render and Vercel projects, deploy once to learn URLs, put the Render URL into `frontend/vercel.json`, set `FRONTEND_ORIGIN`, and re-run the workflow (`workflow_dispatch` or push to `main`).

## Pipeline

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) on `main`:

1. Backend ruff + pytest; frontend format + build
2. `alembic upgrade head` against `DATABASE_URL`
3. [`scripts/deploy-render.sh`](../scripts/deploy-render.sh) upserts Render env vars and triggers a deploy
4. Vercel production build with `VITE_API_BASE_URL` from secrets

PRs run checks only (no deploy).

## Smoke test after deploy

1. Open the Vercel URL → register the first owner.
2. Send a chat message (Hermes/OpenRouter streaming).
3. Create a task from the UI or via the agent.
4. On Telegram page: verify token, start the bot, message from an allowlisted chat.

## Local vs production

| | Local | Production |
| --- | --- | --- |
| UI | Backend serves `frontend/dist` or Vite on `:5173` | Vercel |
| API | `127.0.0.1:8000` | Render |
| `ENVIRONMENT` | `local` | `production` |
| Cookies | `SameSite=strict`, not Secure | `SameSite=none`, Secure |
| DB | SQLite | Supabase Postgres |
| Model | Ollama or Hermes | Hermes + OpenRouter |
