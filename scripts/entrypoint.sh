#!/usr/bin/env bash
set -euo pipefail

# entrypoint.sh — Run migrations then start the API server.
# This replaces the separate prestart container with an inline step.

echo "[entrypoint] Running prestart migrations..."
if ! /app/scripts/prestart.sh; then
    echo "[entrypoint] WARNING: prestart.sh failed. Starting uvicorn anyway."
fi

echo "[entrypoint] Starting uvicorn..."
exec "$@"
