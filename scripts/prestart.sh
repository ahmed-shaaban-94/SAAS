#!/usr/bin/env bash
set -euo pipefail

# prestart.sh — Run SQL migrations in order before the API starts.
# Expects DATABASE_URL or individual PG* env vars to be set.

DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-datapulse}"
DB_USER="${POSTGRES_USER:-datapulse}"

MIGRATIONS_DIR="${MIGRATIONS_DIR:-/app/migrations}"

echo "[prestart] Running SQL migrations from ${MIGRATIONS_DIR}..."

# schema_migrations table tracks which files have been applied
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
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
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -v ON_ERROR_STOP=1 -f "$f"

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -c "INSERT INTO public.schema_migrations (filename) VALUES ('${fname}')"

    applied=$((applied + 1))
done

echo "[prestart] Done. Applied: ${applied}, Skipped: ${skipped}"
