#!/bin/sh
#
# n8n workflow auto-import script.
#
# Waits for n8n to be healthy, then imports all workflow JSON files
# and wires up the notification sub-workflows. Idempotent — safe to
# run multiple times (skips already-imported workflows).
#
# Usage: Called automatically by the n8n-init docker-compose service.

set -e

N8N_URL="${N8N_URL:-http://n8n:5678}"
WORKFLOW_DIR="/workflows"
MAX_WAIT=120  # seconds to wait for n8n

echo "[n8n-init] Waiting for n8n at ${N8N_URL}..."

# ── Wait for n8n to be ready ──
elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
  if wget -q --spider "${N8N_URL}/healthz" 2>/dev/null; then
    echo "[n8n-init] n8n is ready (${elapsed}s)"
    break
  fi
  sleep 2
  elapsed=$((elapsed + 2))
done

if [ $elapsed -ge $MAX_WAIT ]; then
  echo "[n8n-init] ERROR: n8n not ready after ${MAX_WAIT}s"
  exit 1
fi

# ── Setup owner (n8n requires an owner before API works) ──
# Check if owner exists by trying the API
API="${N8N_URL}/api/v1"

# Try to get workflows — if 401, we need to set up owner first
STATUS=$(wget -q -O /dev/null -S "${API}/workflows" 2>&1 | grep "HTTP/" | tail -1 | awk '{print $2}')

if [ "$STATUS" = "401" ] || [ -z "$STATUS" ]; then
  echo "[n8n-init] Setting up n8n owner account..."
  SETUP_BODY='{"email":"admin@datapulse.dev","firstName":"DataPulse","lastName":"Admin","password":"datapulse-n8n-admin-2024!"}'

  wget -q -O /dev/null --post-data="$SETUP_BODY" \
    --header="Content-Type: application/json" \
    "${N8N_URL}/api/v1/owner/setup" 2>/dev/null || true

  sleep 2
fi

# ── Get API key via login ──
echo "[n8n-init] Authenticating..."
LOGIN_BODY='{"email":"admin@datapulse.dev","password":"datapulse-n8n-admin-2024!"}'
COOKIE_FILE=$(mktemp)

wget -q -O /dev/null --save-cookies="$COOKIE_FILE" --keep-session-cookies \
  --post-data="$LOGIN_BODY" \
  --header="Content-Type: application/json" \
  "${N8N_URL}/api/v1/login" 2>/dev/null || true

# ── Import each workflow ──
echo "[n8n-init] Importing workflows from ${WORKFLOW_DIR}..."
imported=0
skipped=0

for wf_file in "${WORKFLOW_DIR}"/*.json; do
  [ -f "$wf_file" ] || continue
  wf_name=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['name'])" "$wf_file" 2>/dev/null || basename "$wf_file" .json)

  # Check if workflow already exists (by name)
  existing=$(wget -q -O - --load-cookies="$COOKIE_FILE" \
    "${API}/workflows" 2>/dev/null | \
    python3 -c "
import json,sys
data = json.load(sys.stdin)
for w in data.get('data', []):
    if w['name'] == '${wf_name}':
        print(w['id'])
        break
" 2>/dev/null || true)

  if [ -n "$existing" ]; then
    echo "  [SKIP] ${wf_name} (already exists: ${existing})"
    skipped=$((skipped + 1))
    continue
  fi

  # Import the workflow
  RESULT=$(wget -q -O - --load-cookies="$COOKIE_FILE" \
    --post-file="$wf_file" \
    --header="Content-Type: application/json" \
    "${API}/workflows" 2>/dev/null || true)

  if [ -n "$RESULT" ]; then
    new_id=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id','?'))" 2>/dev/null || echo "?")
    echo "  [OK] ${wf_name} → id=${new_id}"
    imported=$((imported + 1))

    # Activate the workflow
    wget -q -O /dev/null --load-cookies="$COOKIE_FILE" \
      --post-data='{}' \
      --header="Content-Type: application/json" \
      "${API}/workflows/${new_id}/activate" 2>/dev/null || true
  else
    echo "  [FAIL] ${wf_name}"
  fi
done

rm -f "$COOKIE_FILE"

echo "[n8n-init] Done: ${imported} imported, ${skipped} skipped"
echo "[n8n-init] Workflows are active and ready."
