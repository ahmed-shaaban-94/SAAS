#!/usr/bin/env bash
set -euo pipefail

# entrypoint.sh — Run migrations then start the API server.
# This replaces the separate prestart container with an inline step.

echo "[entrypoint] Running prestart migrations..."
/app/scripts/prestart.sh

echo "[entrypoint] Starting uvicorn..."
exec "$@"
