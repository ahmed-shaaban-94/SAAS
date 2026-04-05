#!/usr/bin/env bash
set -euo pipefail

# prestart.sh — Run SQL migrations in order before the API starts.
# Expects DATABASE_URL or individual PG* env vars to be set.
# For migration 002: set DB_READER_PASSWORD env var for the reader role password.
#
# Environment:
#   SKIP_FAILED_MIGRATIONS=1  — log errors but continue (useful for recovery)
#   DB_CONNECT_RETRIES=10     — number of connection attempts (default: 10)
#   DB_CONNECT_DELAY=3        — seconds between retries (default: 3)

DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-datapulse}"
DB_USER="${POSTGRES_USER:-datapulse}"

MIGRATIONS_DIR="${MIGRATIONS_DIR:-/app/migrations}"
SKIP_FAILED="${SKIP_FAILED_MIGRATIONS:-0}"
MAX_RETRIES="${DB_CONNECT_RETRIES:-10}"
RETRY_DELAY="${DB_CONNECT_DELAY:-3}"

PSQL="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"

# ── Helper: run psql with common flags ──────────────────────────────
run_psql() {
    $PSQL "$@" 2>&1
}

# ── Step 1: Wait for PostgreSQL to be truly ready ───────────────────
echo "[prestart] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
attempt=0
while true; do
    if run_psql -c "SELECT 1" >/dev/null 2>&1; then
        echo "[prestart] PostgreSQL is ready."
        break
    fi
    attempt=$((attempt + 1))
    if [ "$attempt" -ge "$MAX_RETRIES" ]; then
        echo "[prestart] ERROR: Could not connect to PostgreSQL after ${MAX_RETRIES} attempts."
        exit 1
    fi
    echo "[prestart] Connection attempt ${attempt}/${MAX_RETRIES} failed, retrying in ${RETRY_DELAY}s..."
    sleep "$RETRY_DELAY"
done

# ── Step 2: Ensure schema_migrations table exists ───────────────────
echo "[prestart] Ensuring schema_migrations table exists..."
run_psql -v ON_ERROR_STOP=1 <<SQL
CREATE TABLE IF NOT EXISTS public.schema_migrations (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
SQL

# ── Step 3: Run migrations ──────────────────────────────────────────
echo "[prestart] Running SQL migrations from ${MIGRATIONS_DIR}..."

applied=0
skipped=0
failed=0
failed_list=""

for f in "${MIGRATIONS_DIR}"/*.sql; do
    [ -f "$f" ] || continue
    fname="$(basename "$f")"

    # Check if already applied
    already=$(run_psql -tAc "SELECT 1 FROM public.schema_migrations WHERE filename = '${fname}'" 2>/dev/null || echo "")

    if [ "$already" = "1" ]; then
        skipped=$((skipped + 1))
        continue
    fi

    echo "[prestart] Applying: ${fname}"

    # Build psql command — each migration runs in a single transaction
    # so a failure rolls back cleanly (no partial state).
    psql_args="-v ON_ERROR_STOP=1 --single-transaction"

    # Capture output and exit code
    output=""
    rc=0
    if [ -n "${DB_READER_PASSWORD:-}" ]; then
        output=$( (echo "SET app.db_reader_password = '${DB_READER_PASSWORD}';" ; cat "$f") | \
            $PSQL $psql_args 2>&1) || rc=$?
    else
        output=$(run_psql $psql_args -f "$f") || rc=$?
    fi

    if [ "$rc" -ne 0 ]; then
        failed=$((failed + 1))
        failed_list="${failed_list}  - ${fname}\n"
        echo "============================================"
        echo "[prestart] FAILED: ${fname} (exit code ${rc})"
        echo "--------------------------------------------"
        echo "$output"
        echo "============================================"

        if [ "$SKIP_FAILED" = "1" ]; then
            echo "[prestart] SKIP_FAILED_MIGRATIONS=1, continuing..."
            continue
        else
            echo ""
            echo "[prestart] To skip failed migrations and bring the stack up:"
            echo "  Set SKIP_FAILED_MIGRATIONS=1 in the prestart environment."
            echo ""
            exit 1
        fi
    fi

    # Record successful migration
    run_psql -c "INSERT INTO public.schema_migrations (filename) VALUES ('${fname}') ON CONFLICT (filename) DO NOTHING" >/dev/null

    applied=$((applied + 1))
    echo "[prestart] OK: ${fname}"
done

# ── Step 4: Summary ─────────────────────────────────────────────────
echo ""
echo "================================================"
echo "[prestart] Migration summary"
echo "  Applied: ${applied}"
echo "  Skipped: ${skipped} (already applied)"
echo "  Failed:  ${failed}"
if [ -n "$failed_list" ]; then
    echo ""
    echo "  Failed migrations:"
    echo -e "$failed_list"
fi
echo "================================================"

if [ "$failed" -gt 0 ] && [ "$SKIP_FAILED" = "1" ]; then
    echo "[prestart] WARNING: ${failed} migration(s) failed but were skipped."
    echo "[prestart] The stack will start but may have missing schema."
fi

echo "[prestart] Done."
