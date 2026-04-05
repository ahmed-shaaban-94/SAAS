#!/usr/bin/env bash
set -euo pipefail

# prestart.sh — Run SQL migrations in order before the API starts.
# Expects DATABASE_URL or individual PG* env vars to be set.
# For migration 002: set DB_READER_PASSWORD env var for the reader role password.
# If DB_READER_PASSWORD is not set, a random one is generated automatically.

DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-datapulse}"
DB_USER="${POSTGRES_USER:-datapulse}"

MIGRATIONS_DIR="${MIGRATIONS_DIR:-/app/migrations}"

# Auto-generate DB_READER_PASSWORD if not provided
if [ -z "${DB_READER_PASSWORD:-}" ]; then
    DB_READER_PASSWORD="$(openssl rand -hex 16)"
    echo "[prestart] WARNING: DB_READER_PASSWORD not set. Auto-generated a random password for datapulse_reader role."
    echo "[prestart] Set DB_READER_PASSWORD in .env to use a fixed password."
fi

echo "[prestart] Running SQL migrations from ${MIGRATIONS_DIR}..."

# Ensure schema_migrations table exists
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<SQL
CREATE TABLE IF NOT EXISTS public.schema_migrations (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
SQL

applied=0
skipped=0

for f in "${MIGRATIONS_DIR}"/*.sql; do
    fname="$(basename "$f")"

    # Check if already applied
    already=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -tAc "SELECT 1 FROM public.schema_migrations WHERE filename = '${fname}'" 2>/dev/null || echo "")

    if [ "$already" = "1" ]; then
        skipped=$((skipped + 1))
        continue
    fi

    echo "[prestart] Applying: ${fname}"

    # Always prepend GUC setting — harmless for migrations that don't use it,
    # required for migration 002 which checks current_setting('app.db_reader_password')
    (echo "SET app.db_reader_password = '${DB_READER_PASSWORD}';" ; cat "$f") | \
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -c "INSERT INTO public.schema_migrations (filename) VALUES ('${fname}') ON CONFLICT (filename) DO NOTHING"

    applied=$((applied + 1))
done

echo "[prestart] Migrations done. Applied: ${applied}, Skipped: ${skipped}"
echo "[prestart] Done."
