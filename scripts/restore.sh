#!/usr/bin/env bash
set -euo pipefail

# restore.sh — Restore PostgreSQL from a backup file
#
# Usage:
#   ./scripts/restore.sh backups/datapulse_20260404_020000.sql.gz
#
# WARNING: This will DROP and recreate the database. All current data will be lost.

BACKUP_FILE="${1:-}"
CONTAINER="${DB_CONTAINER:-datapulse-db}"
DB_NAME="${POSTGRES_DB:-datapulse}"
DB_USER="${POSTGRES_USER:-datapulse}"

if [ -z "${BACKUP_FILE}" ]; then
    echo "Usage: ./scripts/restore.sh <backup-file>"
    echo ""
    echo "Available backups:"
    ls -lh backups/datapulse_*.sql.gz 2>/dev/null || echo "  (none found in ./backups/)"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "[restore] ERROR: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "[restore] WARNING: This will DROP and recreate database '${DB_NAME}'"
echo "[restore] Source: ${BACKUP_FILE}"
echo "[restore] Press Ctrl+C within 5 seconds to abort..."
sleep 5

echo "[restore] Starting restore at $(date -Iseconds)"

# Copy backup into the container
docker cp "${BACKUP_FILE}" "${CONTAINER}:/tmp/restore.sql.gz"

# Terminate existing connections and restore
docker exec "${CONTAINER}" bash -c "
    psql -U ${DB_USER} -d postgres -c \"
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();
    \"
    dropdb -U ${DB_USER} --if-exists ${DB_NAME}
    createdb -U ${DB_USER} ${DB_NAME}
    pg_restore -U ${DB_USER} -d ${DB_NAME} --verbose /tmp/restore.sql.gz
    rm -f /tmp/restore.sql.gz
"

echo "[restore] Restore complete at $(date -Iseconds)"
echo "[restore] Run 'make dbt' to rebuild silver/gold layers if needed"
