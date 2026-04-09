#!/usr/bin/env bash
set -euo pipefail

# entrypoint.sh — Run migrations then start the API server.

echo "[entrypoint] Running prestart migrations..."
if ! /app/scripts/prestart.sh; then
    echo "[entrypoint] ERROR: prestart.sh failed — aborting startup."
    exit 1
fi

echo "[entrypoint] Starting uvicorn..."
# exec replaces the shell process so SIGTERM reaches uvicorn directly
exec "$@"
