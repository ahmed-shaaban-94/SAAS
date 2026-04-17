#!/usr/bin/env bash
set -euo pipefail

# ── DataPulse POS Desktop Build Script ──────────────────────
# Builds the Next.js frontend (standalone) and packages it
# into an Electron Windows installer.
#
# Usage:
#   cd pos-desktop
#   bash scripts/build.sh          # Full build + package
#   bash scripts/build.sh --dev    # Build only, no packaging

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
POS_DIR="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$(dirname "$POS_DIR")/frontend"
RESOURCES_DIR="$POS_DIR/resources/nextjs"

DEV_MODE=false
if [ "${1:-}" = "--dev" ]; then
  DEV_MODE=true
fi

echo "=== DataPulse POS Desktop Build ==="
echo "Frontend: $FRONTEND_DIR"
echo "Output:   $RESOURCES_DIR"
echo ""

# ── Step 1: Build Next.js (standalone) ──────────────────────
echo "[1/4] Building Next.js frontend..."
cd "$FRONTEND_DIR"

# Set production env vars for the build
export NEXT_PUBLIC_API_URL="https://smartdatapulse.tech"
export NEXT_PUBLIC_FEATURE_PLATFORM="true"
export NEXT_PUBLIC_FEATURE_CONTROL_CENTER="true"

npm run build

echo "[OK] Next.js build complete"

# ── Step 2: Copy standalone output ──────────────────────────
echo "[2/4] Copying standalone output to resources..."
rm -rf "$RESOURCES_DIR"
mkdir -p "$RESOURCES_DIR"

# Copy the standalone server
cp -r "$FRONTEND_DIR/.next/standalone/." "$RESOURCES_DIR/"

# Copy static assets (not included in standalone by default)
mkdir -p "$RESOURCES_DIR/.next/static"
cp -r "$FRONTEND_DIR/.next/static/." "$RESOURCES_DIR/.next/static/"

# Copy public assets
if [ -d "$FRONTEND_DIR/public" ]; then
  cp -r "$FRONTEND_DIR/public" "$RESOURCES_DIR/public"
fi

# Copy messages (next-intl)
if [ -d "$FRONTEND_DIR/messages" ]; then
  cp -r "$FRONTEND_DIR/messages" "$RESOURCES_DIR/messages"
fi

echo "[OK] Resources copied"

# ── Step 3: Compile Electron TypeScript ─────────────────────
echo "[3/4] Compiling Electron TypeScript..."
cd "$POS_DIR"
npm run build

echo "[OK] Electron compiled"

# ── Step 4: Package (skip in dev mode) ──────────────────────
if [ "$DEV_MODE" = true ]; then
  echo "[SKIP] Packaging skipped (--dev mode)"
  echo ""
  echo "To run in dev mode:"
  echo "  cd pos-desktop && npm start"
else
  echo "[4/4] Packaging Electron app..."
  npm run package
  echo ""
  echo "[OK] Installer created in: $POS_DIR/dist/"
  ls -lh "$POS_DIR/dist/"*.exe 2>/dev/null || echo "(no .exe found — check dist/)"
fi

echo ""
echo "=== Build Complete ==="
