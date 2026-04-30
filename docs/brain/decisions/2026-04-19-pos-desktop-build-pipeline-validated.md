---
date: 2026-04-19
branch: main
layers: [frontend, pos]
modules: [pos-desktop, frontend]
---
# Decision: POS desktop build pipeline validated end-to-end

## What happened

First successful end-to-end build of the POS desktop on 2026-04-19. The chain
`frontend/` (Next.js standalone) → `pos-desktop/resources/nextjs/` →
`electron-builder` → `dist/win-unpacked/DataPulse POS.exe` now works without
manual intervention. M1 (backend foundations) → M2 (SQLite + IPC) → M3a/b/c
(sync + hardware + updater) have all shipped into `main`, and the packaging
step is no longer theoretical.

## Outputs verified

- `pos-desktop/dist/win-unpacked/DataPulse POS.exe` — 180 MB Electron binary
- `pos-desktop/dist/win-unpacked/resources/app.asar` — 5.2 MB packed main
  process + preload code
- `pos-desktop/dist/win-unpacked/resources/nextjs/server.js` — standalone
  Next.js server (loads at `http://localhost:3847/terminal` from the main
  process per `docs/plans/specs/2026-04-17-pos-electron-desktop-design.md`)
- `pos-desktop/dist/win-unpacked/resources/app.asar.unpacked/` — native modules
  including `better-sqlite3` rebuilt for Electron's Node ABI

## Key preconditions that had to be true

1. `frontend/next.config.mjs` sets `output: "standalone"` — confirms `server.js`
   gets produced (required for Electron to bootstrap)
2. `frontend/package.json` has `@radix-ui/react-dialog` installed — otherwise
   `marketing/lead-capture-modal.tsx` breaks the webpack compile. Local stale
   `node_modules` caused the first build attempt to fail with
   `Module not found: Can't resolve '@radix-ui/react-dialog'`; `npm install`
   fixed it. CI works because Docker does a clean `npm ci --ignore-scripts`.
3. Placeholder icons exist at `pos-desktop/assets/icon.ico|png` + `tray.png`
   — electron-builder fails without them (wired via `electron-builder.yml`).
   These are Pillow-generated placeholders; real branded art is still owed.
4. Auto-updater `publish:` block uncommented in `electron-builder.yml` — not
   required for the build to succeed, but required for published releases.

## Gotchas encountered

- **`set -euo pipefail` in `scripts/build.sh` doesn't propagate through an
  outer `| tee`.** First build attempt showed `EXIT=0` from `tee` even though
  Next.js had failed. Real exit code lives inside the pipeline; capture with
  `bash scripts/build.sh --dev > log 2>&1; echo "EXIT=$?"` instead.
- **Symlink warnings during `winCodeSign` extraction** (`Cannot create
  symbolic link ... libcrypto.dylib / libssl.dylib`) are darwin signing tools
  we never use (`win` target only). In `npm run package:dir` (no installer)
  they are **non-fatal** — the unpacked app builds cleanly. In
  `npm run package` (full NSIS installer) they become **fatal**: extraction
  retries 3× then fails, preventing `.exe` installer creation.
  - Workarounds: (a) enable Windows Developer Mode for current user to grant
    symlink privilege; (b) run the build as Administrator; (c) pre-extract
    the 7z archive once with elevation, then builder reuses the cache; (d)
    run packaging in CI (Linux host with wine, or Windows runner with proper
    perms) — no dev-machine setup needed.
  - Impact: `dist/win-unpacked/DataPulse POS.exe` is a runnable Electron
    binary even without the NSIS installer. CI will produce the signed
    installer; local dev machines don't need to.

## What's still owed before v1.0

- Replace placeholder icons with final branded artwork
- Code signing (for Windows SmartScreen) — `electron-builder.yml::win` has no
  cert yet; the installer is unsigned
- Actual smoke test — launch `DataPulse POS.exe`, complete Auth0 login, scan
  a barcode, complete a test transaction, unplug network, verify provisional
  queue + sync
- `GITHUB_TOKEN` environment for auto-updater to publish `latest.yml` alongside
  the installer on GitHub Releases

## Why this matters

Prior to today, M1/M2/M3 could only be test-validated in isolation (Jest, pytest).
There was no proof the layers actually compose into a runnable desktop app —
the scaffolding could have hidden integration breakage (bundler excludes,
native module mismatches, missing resources). This build closes that gap:
everything from the Python POS endpoints through the Electron main process
IPC to the Next.js renderer resolves and packages.

## Links

- PR #444 — M3 finish (hooks, tests, icons, auto-updater config)
- PR #446 — IPC handler test coverage (0% → 100%)
- Spec — `docs/plans/specs/2026-04-17-pos-electron-desktop-design.md`
- Previous milestone — PR #434 M3c real hardware adapters + electron-updater
