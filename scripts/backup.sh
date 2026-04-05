#!/usr/bin/env bash
set -euo pipefail

# backup.sh — Automated PostgreSQL backup for DataPulse
#
# Creates a compressed pg_dump of the datapulse database with timestamp.
# Designed for cron scheduling or manual invocation.
#
# Usage:
#   ./scripts/backup.sh                     # Backup to default dir
#   BACKUP_DIR=/mnt/backups ./scripts/backup.sh  # Custom backup dir
#   BACKUP_RETENTION_DAYS=30 ./scripts/backup.sh # Custom retention
#
# Cron example (daily at 2 AM):
#   0 2 * * * cd /path/to/SAAS && ./scripts/backup.sh >> /var/log/datapulse-backup.log 2>&1

BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
CONTAINER="${DB_CONTAINER:-datapulse-db}"
DB_NAME="${POSTGRES_DB:-datapulse}"
DB_USER="${POSTGRES_USER:-datapulse}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/datapulse_${TIMESTAMP}.sql.gz"

echo "[backup] Starting PostgreSQL backup at $(date -Iseconds)"
echo "[backup] Container: ${CONTAINER}"
echo "[backup] Database: ${DB_NAME}"
echo "[backup] Output: ${BACKUP_FILE}"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Check container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "[backup] ERROR: Container '${CONTAINER}' is not running"
    exit 1
fi

# Run pg_dump inside the container, compress, and save locally
docker exec "${CONTAINER}" pg_dump \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --format=custom \
    --compress=6 \
    --verbose \
    2>&1 > "${BACKUP_FILE}" || {
        echo "[backup] ERROR: pg_dump failed"
        rm -f "${BACKUP_FILE}"
        exit 1
    }

# Verify backup file is not empty
BACKUP_SIZE=$(stat -c%s "${BACKUP_FILE}" 2>/dev/null || stat -f%z "${BACKUP_FILE}" 2>/dev/null || echo "0")
if [ "${BACKUP_SIZE}" -lt 1024 ]; then
    echo "[backup] ERROR: Backup file too small (${BACKUP_SIZE} bytes), likely corrupt"
    rm -f "${BACKUP_FILE}"
    exit 1
fi

echo "[backup] Backup complete: ${BACKUP_FILE} ($(du -h "${BACKUP_FILE}" | cut -f1))"

# Clean up old backups
if [ "${BACKUP_RETENTION_DAYS}" -gt 0 ]; then
    DELETED=$(find "${BACKUP_DIR}" -name "datapulse_*.sql.gz" -type f -mtime "+${BACKUP_RETENTION_DAYS}" -delete -print | wc -l)
    if [ "${DELETED}" -gt 0 ]; then
        echo "[backup] Cleaned up ${DELETED} backup(s) older than ${BACKUP_RETENTION_DAYS} days"
    fi
fi

echo "[backup] Done at $(date -Iseconds)"
