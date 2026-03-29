# ── Base stage: system deps + Python packages ──────────────────────
FROM python:3.12-slim-bookworm AS base

WORKDIR /app

# git needed for dbt package resolution
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to fix known CVEs
RUN pip install --no-cache-dir --upgrade pip

# Copy project metadata and source
COPY pyproject.toml .
COPY src/ src/
COPY dbt/ dbt/
COPY migrations/ migrations/

# ── API stage: lightweight, no jupyterlab ──────────────────────────
FROM base AS api

RUN pip install --no-cache-dir "."

RUN useradd -m -u 1000 appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "datapulse.api.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]

# ── App stage: full tooling with jupyterlab ────────────────────────
FROM base AS app

RUN pip install --no-cache-dir "." jupyterlab

RUN useradd -m -u 1000 appuser
USER appuser

EXPOSE 8888

# Default command: keep container running for interactive use
CMD ["tail", "-f", "/dev/null"]
