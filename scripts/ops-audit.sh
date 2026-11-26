#!/usr/bin/env bash
# List every Render service/database and Supabase project the stored keys can see, and
# optionally delete ones that are NOT this project. Default is list-only.
#
#   DELETE_RENDER_IDS="srv-aaa,dpg-bbb"   comma list of Render resource ids to delete
#   DELETE_SUPABASE_REFS="abcdefgh"       comma list of Supabase project refs to delete
#
# The configured RENDER_SERVICE_ID and SUPABASE_PROJECT_REF are never deleted.
set -euo pipefail

: "${RENDER_API_KEY:?RENDER_API_KEY is required}"
KEEP_RENDER="${RENDER_SERVICE_ID:-}"
KEEP_SUPABASE="${SUPABASE_PROJECT_REF:-}"
R="https://api.render.com/v1"
RH="Authorization: Bearer ${RENDER_API_KEY}"

show() { python3 -c "$1"; }

echo "== Render web services / workers / static sites =="
curl -fsS -H "$RH" -H "Accept: application/json" "$R/services?limit=100" | show '
import json, sys
for row in json.load(sys.stdin):
    s = row["service"]
    d = s.get("serviceDetails") or {}
    print(s["id"], s["type"], s["name"], "plan=" + str(d.get("plan")), "suspended=" + str(s.get("suspended")), d.get("url", ""), sep="\t")
'
echo "== Render Postgres =="
curl -fsS -H "$RH" "$R/postgres?limit=100" | show '
import json, sys
for row in json.load(sys.stdin):
    p = row["postgres"]
    print(p["id"], "postgres", p["name"], "plan=" + str(p.get("plan")), sep="\t")
' || true
echo "== Render Key Value =="
curl -fsS -H "$RH" "$R/key-value?limit=100" | show '
import json, sys
for row in json.load(sys.stdin):
    p = row["keyValue"]
    print(p["id"], "key-value", p["name"], sep="\t")
' || true
echo "keeping Render service: ${KEEP_RENDER:-<none set>}"

if [ -n "${SUPABASE_ACCESS_TOKEN:-}" ]; then
  echo "== Supabase projects =="
  curl -fsS -H "Authorization: Bearer ${SUPABASE_ACCESS_TOKEN}" https://api.supabase.com/v1/projects | show '
import json, sys
for p in json.load(sys.stdin):
    print(p["id"], p["name"], p.get("region"), p.get("status"), sep="\t")
'
  echo "keeping Supabase project: ${KEEP_SUPABASE:-<none set>}"
fi

delete_list() { tr ',' '\n' <<<"$1" | sed 's/ //g' | grep -v '^$' || true; }

for id in $(delete_list "${DELETE_RENDER_IDS:-}"); do
  if [ "$id" = "$KEEP_RENDER" ]; then echo "refusing to delete the kept service $id"; continue; fi
  case "$id" in
    dpg-*) path="postgres/$id" ;;
    red-*) path="key-value/$id" ;;
    *) path="services/$id" ;;
  esac
  echo "deleting Render $path"
  curl -fsS -X DELETE -H "$RH" "$R/$path" >/dev/null && echo "deleted $id"
done

for ref in $(delete_list "${DELETE_SUPABASE_REFS:-}"); do
  if [ "$ref" = "$KEEP_SUPABASE" ]; then echo "refusing to delete the kept project $ref"; continue; fi
  echo "deleting Supabase project $ref"
  curl -fsS -X DELETE -H "Authorization: Bearer ${SUPABASE_ACCESS_TOKEN}" \
    "https://api.supabase.com/v1/projects/$ref" >/dev/null && echo "deleted $ref"
done
