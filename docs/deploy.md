# Cloud deploy (Vercel + Render + Supabase)

Production layout for **AURA Personal Agent Hub**:

- **Frontend** → Vercel (`frontend/`) — Product Hub–style SPA
- **Backend** → Render Docker (`backend/Dockerfile`, `render.yaml`) — control plane
- **Database** → Supabase Postgres (pooler URL)
- **Model** → **Local Ollama only** on your machine (Render uses `PERSONAL_AGENT_PROVIDER=fake`)
- **Secrets** → GitHub Environment `production`; Actions sync them to Render/Vercel

Real chat inference against Hermes/Ollama runs on your laptop via `personal-agent dashboard`. The cloud API still serves auth, hub state, Telegram worker control, Google OAuth status, tasks, and approvals.

## One-time platform setup

### 1. Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. Copy the **pooler** connection string → GitHub secret `DATABASE_URL`.
3. Alembic (`hub_workspace`, `google_connections`, …) runs in CI and on container start.

### 2. Render

1. Connect the GitHub repo; web service from `render.yaml` (Docker).
2. Note service id → `RENDER_SERVICE_ID`; API key → `RENDER_API_KEY`.
3. Put the service URL into [`frontend/vercel.json`](../frontend/vercel.json) as the `/api/:path*` rewrite target.

### 3. Vercel

1. Import the repo; **Root Directory** = `frontend`.
2. `cd frontend && npx vercel link` → store `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.
3. Set `FRONTEND_ORIGIN` to your production origin (comma-separated if you use several), e.g.
   `https://personal-ai-agent-mikias-projects-608aa59d.vercel.app`.
   Production also accepts `https://personal-ai-agent*.vercel.app` deploy URLs automatically.
4. Leave `VITE_API_BASE_URL` empty so the SPA uses same-origin `/api`.

### 4. Dashboard + integrations

| Secret | Purpose |
| --- | --- |
| `DASHBOARD_SECRET_KEY` | Session signing (≥ 32 chars) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_ALLOWED_CHAT_IDS` | Optional Telegram |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` | Optional Google OAuth |

For Google in production, set `GOOGLE_REDIRECT_URI` to  
`https://<your-render-host>/api/google/callback` and allow that URI in Google Cloud Console.

### 5. GitHub Environment `production`

Add the secrets listed in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).  
Also add repository secret `DATABASE_URL` for [`.github/workflows/keep-supabase-awake.yml`](../.github/workflows/keep-supabase-awake.yml).

## Pipeline

On `main` (and `workflow_dispatch`):

1. Backend ruff + pytest; frontend Prettier + build
2. `alembic upgrade head` against `DATABASE_URL`
3. [`scripts/deploy-render.sh`](../scripts/deploy-render.sh) upserts env (provider=`fake`) and deploys Render
4. Vercel production build with same-origin `/api`
5. Smoke `GET /api/health` on Render

PRs run checks only.

## Smoke test after deploy

1. Open the Vercel URL → register / sign in.
2. Confirm Dashboard + channel sidebar (Telegram, Google, social scaffolds).
3. Open **My Agent** (cloud uses fake provider until you run locally with Ollama).
4. Telegram / Google connect pages show honest status (no fake metrics).

## Local vs production

| | Local | Production |
| --- | --- | --- |
| UI | Vite `:5173` or `frontend/dist` | Vercel |
| API | `127.0.0.1:8000` | Render |
| `ENVIRONMENT` | `local` | `production` |
| Model | Ollama / Hermes | `fake` on Render |
| DB | SQLite | Supabase Postgres |
