#!/usr/bin/env bash
# smoke-test.sh — Post-deploy smoke tests for DataPulse API.
#
# Validates that the API is alive, the database is reachable, and the auth
# chain can serve authenticated requests. Exits non-zero on any blocking
# failure so the deploy workflow can trigger an automatic rollback.
#
# Usage:
#   bash scripts/smoke-test.sh [--api-key KEY]
#
# Environment:
#   API_KEY           — API key for authenticated smoke tests (optional,
#                       falls back to --api-key flag)
#   SMOKE_TEST_HOST   — Hostname for HTTPS tests (default: localhost)
#   INTERNAL_PORT     — Nginx internal port (default: 8080)

set -euo pipefail

API_KEY="${API_KEY:-}"
HOST="${SMOKE_TEST_HOST:-localhost}"
PORT="${INTERNAL_PORT:-8080}"

# Parse --api-key flag
while [[ $# -gt 0 ]]; do
  case $1 in
    --api-key) API_KEY="$2"; shift 2 ;;
    *) shift ;;
  esac
done

PASS=0
FAIL=0
WARN=0

check() {
  local name="$1" url="$2" expected="$3" blocking="${4:-true}"
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 "$url" 2>/dev/null || echo "000")
  if [ "$code" = "$expected" ]; then
    echo "  PASS: $name ($code)"
    PASS=$((PASS + 1))
  elif [ "$blocking" = "true" ]; then
    echo "  FAIL: $name — expected $expected, got $code"
    FAIL=$((FAIL + 1))
  else
    echo "  WARN: $name — expected $expected, got $code (non-blocking)"
    WARN=$((WARN + 1))
  fi
}

check_not() {
  local name="$1" url="$2" rejected="$3" blocking="${4:-true}"
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 "$url" 2>/dev/null || echo "000")
  if [ "$code" != "$rejected" ] && [ "$code" != "000" ]; then
    echo "  PASS: $name ($code, not $rejected)"
    PASS=$((PASS + 1))
  elif [ "$blocking" = "true" ]; then
    echo "  FAIL: $name — got $rejected (auth chain broken?)"
    FAIL=$((FAIL + 1))
  else
    echo "  WARN: $name — got $code (non-blocking)"
    WARN=$((WARN + 1))
  fi
}

echo "=== DataPulse Smoke Tests ==="
echo "Host: $HOST | Internal port: $PORT"
echo ""

# --- Tier 1: Infrastructure (blocking) ---
echo "[Tier 1] Infrastructure"
check "Liveness"  "http://localhost:$PORT/health/live"  "200"
check "Readiness" "http://localhost:$PORT/health/ready" "200"
check "Auth pipeline" "http://localhost:$PORT/health/auth-check" "200"
echo ""

# --- Tier 2: Auth chain (blocking if API_KEY is set) ---
if [ -n "$API_KEY" ]; then
  echo "[Tier 2] Authenticated endpoints"
  # API_KEY auth bypasses JWT — if this returns 401, the auth middleware itself
  # is broken (not just a missing tenant_id in JWT).
  SUMMARY_URL="https://$HOST/api/v1/analytics/summary"
  code=$(curl -skL -o /dev/null -w '%{http_code}' \
    -H "Host: smartdatapulse.tech" \
    -H "X-API-Key: $API_KEY" \
    "$SUMMARY_URL" 2>/dev/null || echo "000")
  if [ "$code" = "401" ]; then
    echo "  FAIL: /api/v1/analytics/summary with API key returned 401 (auth chain broken)"
    FAIL=$((FAIL + 1))
  elif [ "$code" = "200" ]; then
    echo "  PASS: /api/v1/analytics/summary ($code)"
    PASS=$((PASS + 1))
  else
    echo "  WARN: /api/v1/analytics/summary returned $code (non-blocking)"
    WARN=$((WARN + 1))
  fi
  echo ""
else
  echo "[Tier 2] Skipped — no API_KEY set"
  echo ""
fi

# --- Summary ---
echo "=== Results: $PASS passed, $FAIL failed, $WARN warnings ==="

if [ "$FAIL" -gt 0 ]; then
  echo "::error::Smoke tests FAILED ($FAIL blocking failures)"
  exit 1
fi

echo "All blocking checks passed."
exit 0
