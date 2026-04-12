#!/usr/bin/env bash
set -euo pipefail

# entrypoint.sh — Wait for DB, run migrations, then start the API server.

DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${POSTGRES_USER:-datapulse}"
DB_NAME="${POSTGRES_DB:-datapulse}"

# Wait for PostgreSQL to accept connections (up to 60s)
echo "[entrypoint] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
for i in $(seq 1 12); do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -q 2>/dev/null; then
        echo "[entrypoint] PostgreSQL is ready."
        break
    fi
    if [ "$i" = "12" ]; then
        echo "[entrypoint] ERROR: PostgreSQL not ready after 60s — aborting."
        exit 1
    fi
    sleep 5
done

echo "[entrypoint] Running prestart migrations..."
if ! /app/scripts/prestart.sh; then
    echo "[entrypoint] ERROR: prestart.sh failed — aborting startup."
    exit 1
fi

echo "[entrypoint] Starting server..."
# exec replaces the shell process so SIGTERM reaches uvicorn directly
exec "$@"
