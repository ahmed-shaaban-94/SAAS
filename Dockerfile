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

# ── API stage: production server ─────────────────────────────────
FROM base AS api

RUN pip install --no-cache-dir "."

# Include migration scripts — entrypoint runs them before uvicorn
COPY scripts/prestart.sh /app/scripts/prestart.sh
COPY scripts/entrypoint.sh /app/scripts/entrypoint.sh
RUN sed -i 's/\r$//' /app/scripts/prestart.sh /app/scripts/entrypoint.sh \
    && chmod +x /app/scripts/prestart.sh /app/scripts/entrypoint.sh

RUN useradd -m -u 1000 appuser
USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["uvicorn", "datapulse.api.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
