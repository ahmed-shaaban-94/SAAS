#!/usr/bin/env bash
# Local patch-coverage check — catches the "CI fails on codecov/patch" loop.
#
# Runs the same unit-test + coverage.xml generation CI does, then uses
# `diff-cover` to measure the fraction of lines YOU CHANGED that are
# covered by those tests. Matches the codecov/patch target (81 %).
#
# Cost: ~75 s for the pytest run + <1 s for diff-cover.
#
# Usage:
#   bash scripts/check_diff_coverage.sh           # defaults: base=origin/main, threshold=81
#   DIFF_COVER_THRESHOLD=90 bash scripts/check_diff_coverage.sh
#   DIFF_COVER_BASE=origin/develop bash scripts/check_diff_coverage.sh
#   SKIP_DIFF_COVER=1 bash scripts/check_diff_coverage.sh   # escape hatch
#
# Escape hatch: `SKIP_DIFF_COVER=1` is for emergency pushes only — use
# sparingly so the signal doesn't erode.
#
# Install the tool once: `pip install -e '.[dev]'` (adds diff-cover).

set -euo pipefail

if [[ "${SKIP_DIFF_COVER:-0}" == "1" ]]; then
  echo "[diff-cover] SKIP_DIFF_COVER=1 — skipping patch coverage check."
  exit 0
fi

if ! command -v diff-cover >/dev/null 2>&1; then
  echo "[diff-cover] Not installed. Run:  pip install -e '.[dev]'" >&2
  echo "[diff-cover] Or set SKIP_DIFF_COVER=1 to bypass this one run." >&2
  exit 2
fi

THRESHOLD="${DIFF_COVER_THRESHOLD:-81}"
BASE="${DIFF_COVER_BASE:-origin/main}"

# Make sure we compare against the latest base.
git fetch --quiet origin "${BASE#origin/}" 2>/dev/null || true

# Generate coverage.xml if it's missing or older than 5 minutes — keeps
# repeated runs of this script fast when you're iterating on tests.
if [[ ! -f coverage.xml ]] || [[ -n "$(find coverage.xml -mmin +5 2>/dev/null)" ]]; then
  echo "[diff-cover] coverage.xml stale or missing — running unit tests..."
  pytest -m unit --timeout=120 \
    --cov=datapulse \
    --cov-report=xml \
    --cov-report=term-missing:skip-covered \
    -q
else
  echo "[diff-cover] Reusing coverage.xml (<5 min old)."
fi

echo "[diff-cover] Checking patch coverage vs ${BASE} (threshold ${THRESHOLD} %)…"
diff-cover coverage.xml \
  --compare-branch="${BASE}" \
  --fail-under="${THRESHOLD}" \
  --show-uncovered
