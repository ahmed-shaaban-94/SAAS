# ── Base stage: system deps + Python packages ──────────────────────
FROM python:3.12-slim-bookworm AS base

WORKDIR /app

# git needed for dbt package resolution, postgresql-client for migrations
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends git postgresql-client \
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

COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock \
    && pip install --no-cache-dir --no-deps .

# Tell datapulse.lineage.parser where to find dbt models at runtime
ENV APP_ROOT=/app

# Include migration scripts — entrypoint runs them before uvicorn
COPY gunicorn.conf.py /app/gunicorn.conf.py
COPY scripts/prestart.sh /app/scripts/prestart.sh
COPY scripts/entrypoint.sh /app/scripts/entrypoint.sh
RUN sed -i 's/\r$//' /app/scripts/prestart.sh /app/scripts/entrypoint.sh \
    && chmod +x /app/scripts/prestart.sh /app/scripts/entrypoint.sh

RUN useradd -m -u 1000 appuser
USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["gunicorn", "datapulse.api.app:create_app()", "--config", "/app/gunicorn.conf.py"]
