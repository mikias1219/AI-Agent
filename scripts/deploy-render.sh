#!/usr/bin/env bash
# Upsert Render env vars from GitHub secrets, then trigger a deploy.
# Prefer openai (free Groq/OpenRouter via HERMES_* or OPENAI_COMPAT_*) when a key exists;
# otherwise fall back to fake so the control plane still boots without a laptop Ollama.
set -euo pipefail

: "${RENDER_API_KEY:?RENDER_API_KEY is required}"
: "${RENDER_SERVICE_ID:?RENDER_SERVICE_ID is required}"

API="https://api.render.com/v1/services/${RENDER_SERVICE_ID}"
AUTH_HEADER="Authorization: Bearer ${RENDER_API_KEY}"

sync_env() {
  local key="$1"
  local value="${2:-}"
  if [ -z "$value" ]; then
    echo "skip empty $key"
    return 0
  fi
  echo "upsert $key"
  body=$(VAL="$value" python3 -c 'import json,os; print(json.dumps({"value": os.environ["VAL"]}))')
  curl -fsS -X PUT "${API}/env-vars/${key}" \
    -H "$AUTH_HEADER" \
    -H "Accept: application/json" \
    -H "Content-Type: application/json" \
    -d "$body" >/dev/null
}

# Prefer dedicated OPENAI_COMPAT_*; accept HERMES_* already stored in GitHub/Render secrets.
INFER_KEY="${OPENAI_COMPAT_API_KEY:-${HERMES_API_KEY:-}}"
INFER_BASE="${OPENAI_COMPAT_BASE_URL:-${HERMES_BASE_URL:-}}"
INFER_MODEL="${OPENAI_COMPAT_MODEL:-${HERMES_MODEL:-}}"

if [ -n "$INFER_KEY" ]; then
  PROVIDER=openai
else
  PROVIDER=fake
  echo "warning: no OPENAI_COMPAT_API_KEY / HERMES_API_KEY — deploying with provider=fake"
fi

sync_env ENVIRONMENT production
sync_env PERSONAL_AGENT_PROVIDER "$PROVIDER"
sync_env HERMES_DIRECTORY /app/backend/data/hermes
sync_env LOG_LEVEL INFO
sync_env DATABASE_URL "${DATABASE_URL:-}"
sync_env DASHBOARD_SECRET_KEY "${DASHBOARD_SECRET_KEY:-}"
sync_env DASHBOARD_PASSWORD_HASH "${DASHBOARD_PASSWORD_HASH:-}"
sync_env FRONTEND_ORIGIN "${FRONTEND_ORIGIN:-}"
sync_env TELEGRAM_BOT_TOKEN "${TELEGRAM_BOT_TOKEN:-}"
sync_env TELEGRAM_ALLOWED_CHAT_IDS "${TELEGRAM_ALLOWED_CHAT_IDS:-}"
sync_env GOOGLE_CLIENT_ID "${GOOGLE_CLIENT_ID:-}"
sync_env GOOGLE_CLIENT_SECRET "${GOOGLE_CLIENT_SECRET:-}"
# Production callback; local fallback stays registered in the Google OAuth client.
sync_env GOOGLE_REDIRECT_URI "${GOOGLE_REDIRECT_URI:-}"
sync_env HERMES_API_KEY "${HERMES_API_KEY:-}"
sync_env HERMES_BASE_URL "${HERMES_BASE_URL:-}"
sync_env HERMES_MODEL "${HERMES_MODEL:-}"
sync_env HERMES_CONTEXT_TOKENS "${HERMES_CONTEXT_TOKENS:-}"
sync_env OPENAI_COMPAT_API_KEY "${OPENAI_COMPAT_API_KEY:-}"
sync_env OPENAI_COMPAT_BASE_URL "${OPENAI_COMPAT_BASE_URL:-}"
sync_env OPENAI_COMPAT_MODEL "${OPENAI_COMPAT_MODEL:-}"

echo "Triggering Render deploy for ${RENDER_SERVICE_ID} (provider=${PROVIDER})"
curl -fsS -X POST "${API}/deploys" \
  -H "$AUTH_HEADER" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"clearCache":"do_not_clear"}' >/dev/null

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "Render deploy requested for \`${RENDER_SERVICE_ID}\` (provider=\`${PROVIDER}\`)."
    if [ "$PROVIDER" = "openai" ]; then
      echo "Inference base: \`${INFER_BASE:-default Groq}\`; model: \`${INFER_MODEL:-default}\`."
    else
      echo "No free API key synced — chat will stay offline until HERMES_API_KEY or OPENAI_COMPAT_API_KEY is set."
    fi
  } >> "$GITHUB_STEP_SUMMARY"
fi
