#!/usr/bin/env bash
# Upsert Render env vars from GitHub secrets, then trigger a deploy.
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

sync_env ENVIRONMENT production
sync_env PERSONAL_AGENT_PROVIDER hermes
sync_env HERMES_DIRECTORY /app/backend/data/hermes
sync_env HERMES_BASE_URL "${HERMES_BASE_URL:-https://openrouter.ai/api/v1}"
sync_env HERMES_CONTEXT_TOKENS "${HERMES_CONTEXT_TOKENS:-64000}"
sync_env LOG_LEVEL INFO
sync_env DATABASE_URL "${DATABASE_URL:-}"
sync_env DASHBOARD_SECRET_KEY "${DASHBOARD_SECRET_KEY:-}"
sync_env FRONTEND_ORIGIN "${FRONTEND_ORIGIN:-}"
sync_env HERMES_API_KEY "${HERMES_API_KEY:-}"
sync_env HERMES_MODEL "${HERMES_MODEL:-}"
sync_env TELEGRAM_BOT_TOKEN "${TELEGRAM_BOT_TOKEN:-}"
sync_env TELEGRAM_ALLOWED_CHAT_IDS "${TELEGRAM_ALLOWED_CHAT_IDS:-}"

echo "Triggering Render deploy for ${RENDER_SERVICE_ID}"
curl -fsS -X POST "${API}/deploys" \
  -H "$AUTH_HEADER" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"clearCache":"do_not_clear"}' >/dev/null

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  echo "Render deploy requested for \`${RENDER_SERVICE_ID}\`." >> "$GITHUB_STEP_SUMMARY"
fi
