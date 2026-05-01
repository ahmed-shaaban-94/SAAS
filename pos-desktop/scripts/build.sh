#!/usr/bin/env bash
set -euo pipefail

# ── DataPulse POS Desktop Build Script ──────────────────────
# Builds the Vite renderer bundle and packages it into an Electron Windows
# installer. Replaces the prior Next.js standalone embed (Sub-PR 2 of POS
# extraction).
#
# Usage:
#   cd pos-desktop
#   bash scripts/build.sh          # Full build + package
#   bash scripts/build.sh --dev    # Build only, no packaging

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
POS_DIR="$(dirname "$SCRIPT_DIR")"

DEV_MODE=false
if [ "${1:-}" = "--dev" ]; then
  DEV_MODE=true
fi

echo "=== DataPulse POS Desktop Build ==="
echo "Output: $POS_DIR/dist/renderer (Vite bundle), $POS_DIR/dist/electron (TS)"
echo ""

cd "$POS_DIR"

# Production env vars for the renderer build. Vite inlines `import.meta.env.*`
# at build time (the equivalent of Next.js's NEXT_PUBLIC_*).
#
# Clerk publishable key is intentionally hardcoded as a default: it is a
# *public* key (shipped in client bundles by design; see Clerk docs), not a
# secret. CI can override via the env. Never set CLERK_SECRET_KEY here — that
# is a server secret and would leak to every pilot machine.
export VITE_API_URL="${VITE_API_URL:-https://smartdatapulse.tech}"
export VITE_AUTH_PROVIDER="${VITE_AUTH_PROVIDER:-clerk}"
export VITE_CLERK_PUBLISHABLE_KEY="${VITE_CLERK_PUBLISHABLE_KEY:-pk_live_Y2xlcmsuc21hcnRkYXRhcHVsc2UudGVjaCQ}"
export VITE_CLERK_JWT_TEMPLATE="${VITE_CLERK_JWT_TEMPLATE:-datapulse}"
export VITE_CLERK_JWT_FALLBACK_TEMPLATES="${VITE_CLERK_JWT_FALLBACK_TEMPLATES:-datapulse-pos}"
export VITE_CLERK_SIGN_IN_URL="${VITE_CLERK_SIGN_IN_URL:-/sign-in}"
export VITE_CLERK_SIGN_UP_URL="${VITE_CLERK_SIGN_UP_URL:-/sign-up}"

# ── Step 1: Vite renderer build ─────────────────────────────
echo "[1/3] Building Vite renderer..."
npm run build:renderer
echo "[OK] Vite bundle at $POS_DIR/dist/renderer/"

# ── Step 2: Compile Electron TypeScript ─────────────────────
echo "[2/3] Compiling Electron TypeScript..."
npm run build:electron
echo "[OK] Electron compiled"

# ── Step 3: Package (skip in dev mode) ──────────────────────
if [ "$DEV_MODE" = true ]; then
  echo "[SKIP] Packaging skipped (--dev mode)"
  echo ""
  echo "To run the Electron app in dev mode (with hot reload):"
  echo "  cd pos-desktop && npm run dev"
else
  echo "[3/3] Packaging Electron app..."
  npm run package
  echo ""
  echo "[OK] Installer created in: $POS_DIR/dist/"
  ls -lh "$POS_DIR/dist/"*.exe 2>/dev/null || echo "(no .exe found — check dist/)"
fi

echo ""
echo "=== Build Complete ==="
