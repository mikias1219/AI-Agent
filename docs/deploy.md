# Cloud deploy (Vercel + Render + Supabase)

Production layout for **AURA Personal Agent Hub**:

- **Frontend** → Vercel (`frontend/`) — Next.js App Router
- **Backend** → Render Docker (`backend/Dockerfile`, `render.yaml`) — control plane
- **Database** → Supabase Postgres (pooler URL)
- **Model** → Production uses `PERSONAL_AGENT_PROVIDER=openai` (free Groq/OpenRouter via `HERMES_*` or `OPENAI_COMPAT_*` secrets). Locally use Ollama/Hermes.
- **Secrets** → GitHub Environment `production`; Actions sync them to Render/Vercel

Production chat answers come from the OpenAI-compatible cloud endpoint. Without `HERMES_API_KEY` / `OPENAI_COMPAT_API_KEY`, deploy falls back to `fake`. Local Ollama remains available via `personal-agent dashboard`.

## One-time platform setup

### 1. Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. Copy the **pooler** connection string → GitHub secret `DATABASE_URL`.
3. Alembic (`hub_workspace`, `google_connections`, …) runs in CI and on container start.

### 2. Render

1. Connect the GitHub repo; web service from `render.yaml` (Docker).
2. Note service id → `RENDER_SERVICE_ID`; API key → `RENDER_API_KEY`.
3. Put the service URL into [`frontend/vercel.json`](../frontend/vercel.json) as the `/api/:path*` rewrite target.

### 3. Vercel (Next.js)

1. Import the repo; **Root Directory** = `frontend`.
2. Framework Preset = **Next.js** (do not use Vite / `dist`).
3. From `frontend/`: `npx vercel link` → store `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` in GitHub Environment `production`.
4. Set `FRONTEND_ORIGIN` to your production origin (comma-separated if you use several), e.g.
   `https://personal-ai-agent-mikias-projects-608aa59d.vercel.app`.
   Production also accepts `https://personal-ai-agent*.vercel.app` deploy URLs automatically.
5. Leave `NEXT_PUBLIC_API_BASE_URL` empty so the app uses same-origin `/api` (rewritten to Render by `vercel.json`).
6. Remove any leftover `VITE_API_BASE_URL` project env vars from the old Vite setup.

### 4. Dashboard + integrations

| Secret | Purpose |
| --- | --- |
| `DASHBOARD_SECRET_KEY` | Session signing (≥ 32 chars) |
| `HERMES_API_KEY` (+ optional `HERMES_BASE_URL` / `HERMES_MODEL`) | Free cloud inference (Groq/OpenRouter). Or use `OPENAI_COMPAT_*` |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_ALLOWED_CHAT_IDS` | Optional Telegram |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` | Optional Google OAuth |

For Google OAuth (Connections → Google):

1. Google Cloud Console → APIs & Services → Credentials → Create OAuth client ID (Web application).
2. Authorized redirect URI (local): `http://127.0.0.1:8000/api/google/callback`
3. Authorized redirect URI (production API host): `https://<your-render-host>/api/google/callback`
4. Enable **Gmail API**, **Google Calendar API**, and **Google Drive API** for the project.
5. Put `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and matching `GOOGLE_REDIRECT_URI` in `backend/.env` (local) and Render env (production cutover).
6. After connect, the dashboard stores sealed tokens server-side and serves `GET /api/google/gmail|calendar|drive`.

### 5. GitHub Environment `production`

Add the secrets listed in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).  
Also add repository secret `DATABASE_URL` for [`.github/workflows/keep-supabase-awake.yml`](../.github/workflows/keep-supabase-awake.yml).

## Pipeline

On `main` (and `workflow_dispatch`):

1. Backend ruff + pytest; frontend Prettier + Next.js build (scans `.next/`)
2. `alembic upgrade head` against `DATABASE_URL`
3. [`scripts/deploy-render.sh`](../scripts/deploy-render.sh) upserts env (`openai` when a free API key is present) and deploys Render
4. Vercel production build (`framework: nextjs`) with same-origin `/api`
5. Smoke `GET /api/health` on Render

PRs run checks only.

## Smoke test after deploy

1. Open the Vercel URL → register / sign in.
2. Confirm Overview shell + Connections (Telegram live; LinkedIn/Facebook Preview).
3. Open **Chat** — `/api/status` should show `provider: openai` and real answers (not “Okay.”).
4. Google: Connect Google stores tokens and fills Gmail/Calendar/Drive (local `.env` or production `GOOGLE_*` secrets synced to Render).

## Local vs production

| | Local | Production |
| --- | --- | --- |
| UI | Next.js `:3000` (`npm run dev` in `frontend/`) | Vercel (Next.js) |
| API | `127.0.0.1:8000` (Next rewrite) | Render (Vercel `/api` rewrite) |
| `ENVIRONMENT` | `local` | `production` |
| Model | Ollama / Hermes | `openai` (free cloud key) |
| DB | SQLite | Supabase Postgres |
| Google | `GOOGLE_*` in `backend/.env` | GitHub Environment `production` → Render via `deploy-render.sh` |
