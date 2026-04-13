#!/bin/bash
# brain-session-end.sh — Thin wrapper that delegates to Python brain module.
# Trigger: Stop hook (fires when Claude session ends)
# The Python module handles PostgreSQL insert + markdown fallback.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
if [ -z "$PROJECT_DIR" ]; then exit 0; fi
if [ ! -d "$PROJECT_DIR/.git" ] && [ ! -f "$PROJECT_DIR/.git" ]; then exit 0; fi

cd "$PROJECT_DIR"

# Source .env for DATABASE_URL / OPENROUTER_API_KEY
[ -f .env ] && set -a && source .env && set +a

# Find Python — prefer project venv, fall back to system
PYTHON=""
for candidate in \
  "${PROJECT_DIR}/.venv/bin/python" \
  "${PROJECT_DIR}/.venv/Scripts/python.exe" \
  "$(command -v python3 2>/dev/null || true)" \
  "$(command -v python 2>/dev/null || true)"; do
  if [ -n "$candidate" ] && [ -f "$candidate" ]; then
    PYTHON="$candidate"
    break
  fi
done

[ -z "$PYTHON" ] && exit 0

# Run the brain session end script — never block session exit
PYTHONPATH="${PROJECT_DIR}/src" "$PYTHON" -m datapulse.brain.session_end 2>/dev/null || true

exit 0
