#!/usr/bin/env bash
set -euo pipefail

# Manual deploy script for DataPulse — use when CI/CD is not available.
# Usage:
#   ./scripts/deploy-manual.sh --host 1.2.3.4 --user root --key ~/.ssh/id_rsa --path /opt/datapulse
#   ./scripts/deploy-manual.sh -h 1.2.3.4 -u root -k ~/.ssh/id_rsa -p /opt/datapulse

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

HOST=""
USER="root"
KEY=""
DEPLOY_PATH="/opt/datapulse"
GHCR_USER=""
GHCR_TOKEN=""
SKIP_BUILD=false

usage() {
  cat <<EOF
DataPulse Manual Deploy Script

USAGE:
  $(basename "$0") [OPTIONS]

OPTIONS:
  -h, --host HOST          Server IP or hostname (required)
  -u, --user USER          SSH username (default: root)
  -k, --key  KEY           SSH private key path (required)
  -p, --path PATH          Deploy path on server (default: /opt/datapulse)
  -g, --ghcr-user USER     GHCR username for docker login (default: prompts)
  -t, --ghcr-token TOKEN   GHCR token/PAT for docker login (default: prompts)
  --skip-build             Skip image pull, only restart services
  --help                   Show this help message

EXAMPLES:
  # Full deploy with GHCR images
  $(basename "$0") -h 1.2.3.4 -u root -k ~/.ssh/id_rsa

  # Quick restart (no image pull)
  $(basename "$0") -h 1.2.3.4 -u root -k ~/.ssh/id_rsa --skip-build
EOF
  exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--host)     HOST="$2"; shift 2 ;;
    -u|--user)     USER="$2"; shift 2 ;;
    -k|--key)      KEY="$2"; shift 2 ;;
    -p|--path)     DEPLOY_PATH="$2"; shift 2 ;;
    -g|--ghcr-user) GHCR_USER="$2"; shift 2 ;;
    -t|--ghcr-token) GHCR_TOKEN="$2"; shift 2 ;;
    --skip-build)  SKIP_BUILD=true; shift ;;
    --help)        usage ;;
    *)             echo "Unknown option: $1"; usage ;;
  esac
done

# Validate required args
if [[ -z "$HOST" ]]; then
  echo "Error: --host is required"
  exit 1
fi
if [[ -z "$KEY" ]]; then
  echo "Error: --key is required"
  exit 1
fi
if [[ ! -f "$KEY" ]]; then
  echo "Error: SSH key not found: $KEY"
  exit 1
fi

SSH_OPTS="-i $KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
SSH_CMD="ssh $SSH_OPTS $USER@$HOST"
SCP_CMD="scp $SSH_OPTS -r"

echo "=== DataPulse Manual Deploy ==="
echo "Host:   $USER@$HOST"
echo "Path:   $DEPLOY_PATH"
echo "Source: $SCRIPT_DIR"
echo ""

# Step 1: Test SSH connection
echo "[1/5] Testing SSH connection..."
if ! $SSH_CMD "echo 'SSH OK'"; then
  echo "Error: Cannot connect to $USER@$HOST"
  exit 1
fi

# Step 2: Ensure deploy directory exists
echo "[2/5] Preparing deploy directory..."
$SSH_CMD "mkdir -p $DEPLOY_PATH"

# Step 3: Copy files
echo "[3/5] Copying files to server..."
$SCP_CMD \
  "$SCRIPT_DIR/docker-compose.yml" \
  "$SCRIPT_DIR/docker-compose.prod.yml" \
  "$USER@$HOST:$DEPLOY_PATH/"

for dir in nginx migrations postgres; do
  if [[ -d "$SCRIPT_DIR/$dir" ]]; then
    $SCP_CMD "$SCRIPT_DIR/$dir" "$USER@$HOST:$DEPLOY_PATH/"
  fi
done

# Step 4: Deploy
echo "[4/5] Deploying on server..."
if [[ "$SKIP_BUILD" == "true" ]]; then
  $SSH_CMD "cd $DEPLOY_PATH && \
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --remove-orphans"
else
  # Prompt for GHCR credentials if not provided
  if [[ -z "$GHCR_USER" ]]; then
    read -rp "GHCR username (GitHub username): " GHCR_USER
  fi
  if [[ -z "$GHCR_TOKEN" ]]; then
    read -rsp "GHCR token (GitHub PAT): " GHCR_TOKEN
    echo ""
  fi

  $SSH_CMD "cd $DEPLOY_PATH && \
    echo '$GHCR_TOKEN' | docker login ghcr.io -u '$GHCR_USER' --password-stdin && \
    docker compose -f docker-compose.yml -f docker-compose.prod.yml pull api frontend && \
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --remove-orphans"
fi

# Step 5: Health check
echo "[5/5] Running health check..."
PASSED=false
for i in $(seq 1 6); do
  HTTP_CODE=$($SSH_CMD "curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 http://localhost:3000" 2>/dev/null || echo "000")
  if [[ "$HTTP_CODE" == "200" ]]; then
    echo "Health check PASSED on attempt $i (HTTP $HTTP_CODE)"
    PASSED=true
    break
  fi
  echo "Attempt $i: HTTP $HTTP_CODE — retrying in 10s..."
  sleep 10
done

# Show container status
echo ""
echo "=== Container Status ==="
$SSH_CMD "cd $DEPLOY_PATH && docker compose -f docker-compose.yml -f docker-compose.prod.yml ps"

if [[ "$PASSED" == "true" ]]; then
  echo ""
  echo "Deploy successful!"
else
  echo ""
  echo "ERROR: Health check failed after 6 attempts. Check container logs:"
  echo "  ssh $SSH_OPTS $USER@$HOST 'cd $DEPLOY_PATH && docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail 50'"
  exit 1
fi
