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
  # In git worktrees, node_modules lives in the main repo — find tsc there.
  TSC_BIN="frontend/node_modules/.bin/tsc"
  if [ ! -f "$TSC_BIN" ]; then
    MAIN=$(git worktree list --porcelain 2>/dev/null | grep "^worktree " | head -1 | cut -d' ' -f2)
    [ -f "${MAIN}/frontend/node_modules/.bin/tsc" ] && TSC_BIN="${MAIN}/frontend/node_modules/.bin/tsc"
  fi
  if [ -f "$TSC_BIN" ]; then
    # Filter pre-existing errors not caused by our source code:
    #  - vitest/globals config error
    #  - .next/types/* stale build artifacts (worktree / first-build issue)
    #  - @clerk/nextjs missing package (optional dep, not installed in all envs)
    #  - bwip-js / qrcode.react missing packages (optional receipt deps)
    TSC_OUT=$("$TSC_BIN" --project frontend/tsconfig.json --noEmit 2>&1 || true)
    NEW_ERRORS=$(echo "$TSC_OUT" | grep "^frontend/" \
      | grep -v "vitest/globals" \
      | grep -v "\.next/types/" \
      | grep -v "@clerk/nextjs" \
      | grep -v "bwip-js" \
      | grep -v "qrcode\.react" \
      | grep -v "src/middleware\.ts" \
      | grep "error TS" || true)
    if [ -n "$NEW_ERRORS" ]; then
      echo "$NEW_ERRORS" >&2
      ERRORS="${ERRORS}TypeScript type check failed. "
    fi
  else
    echo "[PRE-COMMIT] tsc not found — skipping TypeScript check." >&2
  fi
fi

if [ -n "$ERRORS" ]; then
  echo "[PRE-COMMIT] BLOCKED: ${ERRORS}Fix before committing." >&2
  exit 2
fi

echo "[PRE-COMMIT] All checks passed." >&2
exit 0
