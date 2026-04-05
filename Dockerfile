# ── Base stage: system deps + Python packages ──────────────────────
FROM python:3.12-slim-bookworm AS base

WORKDIR /app

# git needed for dbt package resolution, postgresql-client for migrations
RUN apt-get update && apt-get install -y --no-install-recommends git postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to fix known CVEs
RUN pip install --no-cache-dir --upgrade pip

# Copy project metadata and source
COPY pyproject.toml .
COPY src/ src/
COPY dbt/ dbt/
COPY migrations/ migrations/

# -- Prestart stage: runs SQL migrations ──────────────────────────
FROM base AS prestart

COPY scripts/prestart.sh /app/scripts/prestart.sh
RUN sed -i 's/\r$//' /app/scripts/prestart.sh && chmod +x /app/scripts/prestart.sh

CMD ["/app/scripts/prestart.sh"]

# ── API stage: production server ─────────────────────────────────
FROM base AS api

RUN pip install --no-cache-dir "."

# Include prestart script so prod compose can reuse this image for migrations
COPY scripts/prestart.sh /app/scripts/prestart.sh
RUN sed -i 's/\r$//' /app/scripts/prestart.sh && chmod +x /app/scripts/prestart.sh

RUN useradd -m -u 1000 appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "datapulse.api.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
