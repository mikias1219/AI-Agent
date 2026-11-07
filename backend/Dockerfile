# Production image for Render: FastAPI + Hermes runtime + Alembic.
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HERMES_DIRECTORY=/app/backend/data/hermes \
    ENVIRONMENT=production

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/ /app/backend/

WORKDIR /app/backend
RUN python -m pip install --upgrade pip \
    && python -m pip install -e . \
    && python scripts/setup_hermes.py

COPY backend/scripts/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
