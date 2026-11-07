#!/bin/sh
set -eu
cd /app/backend
alembic upgrade head
exec personal-agent serve --host 0.0.0.0 --port "${PORT:-8000}"
