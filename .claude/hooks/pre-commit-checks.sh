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
  # TypeScript check requires node_modules for accurate type resolution.
  # In git worktrees node_modules lives only in the main worktree, so tsc
  # run from the worktree produces thousands of spurious implicit-any and
  # missing-children errors for files we didn't touch. Skip the check when
  # frontend/node_modules is absent — CI covers the full check in the main tree.
  if [ -d "frontend/node_modules" ]; then
    echo "[PRE-COMMIT] Running tsc --noEmit..." >&2
    TSC_BIN="frontend/node_modules/.bin/tsc"
    if [ -f "$TSC_BIN" ]; then
      TSC_OUT=$("$TSC_BIN" --project frontend/tsconfig.json --noEmit 2>&1 || true)
      NEW_ERRORS=$(echo "$TSC_OUT" | grep "^frontend/" \
        | grep -v "vitest/globals" \
        | grep -v "^frontend/\.next/" \
        | grep -v "error TS2307: Cannot find module" \
        | grep "error TS" || true)
      if [ -n "$NEW_ERRORS" ]; then
        echo "$NEW_ERRORS" >&2
        ERRORS="${ERRORS}TypeScript type check failed. "
      fi
    fi
  else
    echo "[PRE-COMMIT] Skipping tsc (no frontend/node_modules — likely a git worktree)." >&2
  fi
fi

if [ -n "$ERRORS" ]; then
  echo "[PRE-COMMIT] BLOCKED: ${ERRORS}Fix before committing." >&2
  exit 2
fi

echo "[PRE-COMMIT] All checks passed." >&2
exit 0
