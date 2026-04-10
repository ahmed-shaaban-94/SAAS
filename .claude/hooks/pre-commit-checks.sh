#!/bin/bash
# Pre-commit quality gate: lint-checks staged Python/TypeScript files.
# Catches CI failures early — saves follow-up PR loops.

cd "$CLAUDE_PROJECT_DIR" || exit 0

ERRORS=""

# Get staged files
STAGED=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)

# Python backend checks — only if staged .py files exist
PY_FILES=$(echo "$STAGED" | grep '\.py$' || true)
if [ -n "$PY_FILES" ] && command -v ruff &>/dev/null; then
  echo "[PRE-COMMIT] Running ruff check on staged Python files..." >&2
  if ! echo "$PY_FILES" | xargs ruff check --quiet 2>/dev/null; then
    ERRORS="${ERRORS}Python lint (ruff) failed. "
  fi
fi

# TypeScript frontend checks — only if staged .ts/.tsx files exist
TS_FILES=$(echo "$STAGED" | grep -E '\.(ts|tsx)$' || true)
if [ -n "$TS_FILES" ] && [ -f frontend/tsconfig.json ]; then
  echo "[PRE-COMMIT] Running tsc --noEmit..." >&2
  if ! (cd frontend && npx tsc --noEmit 2>/dev/null); then
    ERRORS="${ERRORS}TypeScript type check failed. "
  fi
fi

if [ -n "$ERRORS" ]; then
  echo "[PRE-COMMIT] BLOCKED: ${ERRORS}Fix before committing." >&2
  exit 2
fi

echo "[PRE-COMMIT] All checks passed." >&2
exit 0
